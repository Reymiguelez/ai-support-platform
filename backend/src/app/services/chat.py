import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID

from openai.types.chat import ChatCompletionMessageParam

from app.core.config import settings
from app.core.exceptions import AIServiceException, ValidationException
from app.core.logging import get_logger
from app.domain.models.conversation import Conversation, ConversationStatus, Message, MessageRole
from app.infrastructure.ai.client import openai_client
from app.infrastructure.ai.rag import rag_service
from app.infrastructure.ai.tools import ToolRegistry
from app.infrastructure.repositories.conversation import ConversationRepository, MessageRepository

logger = get_logger(__name__)


class ChatService:
    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo

    async def create_conversation(
        self,
        user_id: UUID,
        title: str = "New Conversation",
        system_prompt: str | None = None,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
    ) -> Conversation:
        conversation = await self.conversation_repo.create(
            user_id=user_id,
            title=title,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            status=ConversationStatus.ACTIVE,
        )
        logger.info(
            "Conversation created", conversation_id=str(conversation.id), user_id=str(user_id)
        )
        return conversation

    async def get_conversation(self, conversation_id: UUID, user_id: UUID) -> Conversation | None:
        conversation = await self.conversation_repo.get(conversation_id)
        if conversation and conversation.user_id == user_id:
            return conversation
        return None

    async def list_conversations(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status: ConversationStatus | None = None,
    ) -> tuple[list[Conversation], int]:
        conversations = await self.conversation_repo.get_by_user(user_id, skip, limit, status)
        total = await self.conversation_repo.count_by_user(user_id, status)
        return list(conversations), total

    async def update_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
        **kwargs,
    ) -> Conversation | None:
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return None
        return await self.conversation_repo.update(conversation, **kwargs)

    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False
        await self.conversation_repo.delete(conversation)
        return True

    async def add_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        role: MessageRole,
        content: str,
        **kwargs,
    ) -> Message:
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValidationException("Conversation not found")

        if role == MessageRole.USER:
            message = await self.message_repo.create_user_message(conversation_id, content)
        else:
            message = await self.message_repo.create_assistant_message(
                conversation_id=conversation_id,
                content=content,
                **kwargs,
            )

        conversation.updated_at = datetime.now(UTC)
        await self.conversation_repo.session.flush()
        return message

    async def get_messages(
        self,
        conversation_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Message]:
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValidationException("Conversation not found")
        messages = await self.message_repo.get_by_conversation(conversation_id, skip, limit)
        return list(messages)

    async def get_recent_messages(
        self,
        conversation_id: UUID,
        user_id: UUID,
        limit: int = 10,
    ) -> list[Message]:
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValidationException("Conversation not found")
        return await self.message_repo.get_recent_by_conversation(conversation_id, limit)

    def _build_messages(
        self,
        conversation: Conversation,
        recent_messages: list[Message],
        user_message: str,
        context: str | None = None,
    ) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = []

        if conversation.system_prompt:
            system_content = conversation.system_prompt
            if context:
                system_content += f"\n\nRelevant context from knowledge base:\n{context}"
            messages.append({"role": "system", "content": system_content})
        elif context:
            messages.append(
                {"role": "system", "content": f"Relevant context from knowledge base:\n{context}"}
            )

        for msg in recent_messages:
            if msg.role == MessageRole.TOOL:
                messages.append(
                    {
                        "role": "tool",
                        "content": msg.content,
                        "tool_call_id": msg.extra_metadata.get("tool_call_id", ""),
                    }
                )
            else:
                messages.append({"role": msg.role.value, "content": msg.content})

        messages.append({"role": "user", "content": user_message})
        return messages

    async def stream_chat(
        self,
        conversation_id: UUID,
        user_id: UUID,
        user_message: str,
        use_rag: bool = True,
        knowledge_base_id: UUID | None = None,
        use_tools: bool = True,
    ) -> AsyncGenerator[str]:
        start_time = time.time()

        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValidationException("Conversation not found")

        await self.add_message(conversation_id, user_id, MessageRole.USER, user_message)

        recent_messages = await self.get_recent_messages(
            conversation_id, user_id, settings.CONVERSATION_MEMORY_WINDOW
        )

        context = None
        if use_rag:
            chunks = await rag_service.search_relevant_chunks(
                query=user_message,
                top_k=settings.VECTOR_SEARCH_TOP_K,
                similarity_threshold=settings.VECTOR_SEARCH_SIMILARITY_THRESHOLD,
                knowledge_base_id=knowledge_base_id,
            )
            if chunks:
                context = await rag_service.build_context(chunks)

        messages = self._build_messages(conversation, recent_messages, user_message, context)

        tools = None
        tool_choice = None
        if use_tools:
            tools = ToolRegistry.get_schemas()
            tool_choice = "auto"

        full_content = ""
        tool_calls = []
        tool_results = []

        try:
            async for chunk in openai_client.chat_completion(
                messages=messages,
                temperature=conversation.temperature,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                tools=tools,
                tool_choice=tool_choice,
                stream=True,
            ):
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    content = delta.content
                    full_content += content
                    yield content

                if delta and delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index >= len(tool_calls):
                            tool_calls.append(
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            )
                        if tc.function.name:
                            tool_calls[tc.index]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

            if tool_calls:
                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    tool_args = tc["function"]["arguments"]
                    tool = ToolRegistry.get(tool_name)
                    if tool:
                        try:
                            import json

                            args = json.loads(tool_args) if tool_args else {}
                            result = await tool.execute(args, user_id)
                            tool_results.append(
                                {
                                    "tool_call_id": tc["id"],
                                    "name": tool_name,
                                    "result": result,
                                }
                            )
                            yield f"\n\n[Tool: {tool_name} executed]\n"
                        except Exception as e:
                            logger.error("Tool execution failed", tool=tool_name, error=str(e))
                            tool_results.append(
                                {
                                    "tool_call_id": tc["id"],
                                    "name": tool_name,
                                    "error": str(e),
                                }
                            )

                if tool_results:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": full_content,
                            "tool_calls": tool_calls,
                        }
                    )
                    for tr in tool_results:
                        messages.append(
                            {
                                "role": "tool",
                                "content": str(tr.get("result", tr.get("error"))),
                                "tool_call_id": tr["tool_call_id"],
                            }
                        )

                    async for chunk in openai_client.chat_completion(
                        messages=messages,
                        temperature=conversation.temperature,
                        max_tokens=settings.OPENAI_MAX_TOKENS,
                        stream=True,
                    ):
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if delta and delta.content:
                            content = delta.content
                            full_content += content
                            yield content

            execution_time_ms = int((time.time() - start_time) * 1000)

            await self.add_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role=MessageRole.ASSISTANT,
                content=full_content,
                tokens=int(len(full_content.split()) * 1.3),
                model=conversation.model,
                execution_time_ms=execution_time_ms,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        except Exception as e:
            logger.error("Chat streaming failed", error=str(e))
            raise AIServiceException(f"Chat failed: {e!s}")

    async def chat(
        self,
        conversation_id: UUID,
        user_id: UUID,
        user_message: str,
        use_rag: bool = True,
        knowledge_base_id: UUID | None = None,
        use_tools: bool = True,
    ) -> Message:
        full_response = ""
        async for chunk in self.stream_chat(
            conversation_id,
            user_id,
            user_message,
            use_rag,
            knowledge_base_id,
            use_tools,
        ):
            full_response += chunk

        conversation = await self.get_conversation(conversation_id, user_id)
        recent_messages = await self.get_recent_messages(conversation_id, user_id, 1)
        return recent_messages[-1] if recent_messages else None
