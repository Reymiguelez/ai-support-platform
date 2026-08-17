from collections.abc import AsyncGenerator

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam

from app.core.config import settings
from app.core.exceptions import AIServiceException
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY or "dummy-key-for-tests",
            organization=settings.OPENAI_ORGANIZATION,
        )
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL

    async def chat_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        stream: bool = False,
    ) -> AsyncGenerator[ChatCompletionChunk | dict]:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                stream=stream,
            )

            if stream:
                async for chunk in response:
                    yield chunk
            else:
                yield response.model_dump()

        except Exception as e:
            logger.error("OpenAI chat completion error", error=str(e))
            raise AIServiceException(f"Chat completion failed: {e!s}")

    async def create_embedding(self, text: str) -> list[float]:
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("OpenAI embedding error", error=str(e))
            raise AIServiceException(f"Embedding creation failed: {e!s}")

    async def create_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error("OpenAI batch embedding error", error=str(e))
            raise AIServiceException(f"Batch embedding creation failed: {e!s}")


openai_client = OpenAIClient()
