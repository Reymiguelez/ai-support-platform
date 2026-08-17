from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.core.logging import get_logger
from app.domain.models.tool import ToolExecution
from app.infrastructure.ai.tools import ToolRegistry
from app.infrastructure.repositories.tool import ToolExecutionRepository, ToolRepository

logger = get_logger(__name__)


class ToolService:
    def __init__(
        self,
        tool_repo: ToolRepository,
        execution_repo: ToolExecutionRepository,
    ):
        self.tool_repo = tool_repo
        self.execution_repo = execution_repo

    async def get_available_tools(self, user_permissions: list[str] = None) -> list:
        if user_permissions:
            return ToolRegistry.get_schemas_by_permissions(user_permissions)
        return ToolRegistry.get_schemas()

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        user_id: UUID,
        conversation_id: UUID | None = None,
        message_id: UUID | None = None,
    ) -> ToolExecution:
        tool = ToolRegistry.get(tool_name)
        if not tool:
            from app.core.exceptions import NotFoundException

            raise NotFoundException("Tool", tool_name)

        execution = await self.execution_repo.create_execution(
            tool_id=(
                tool.id if hasattr(tool, "id") else UUID("00000000-0000-0000-0000-000000000000")
            ),
            user_id=user_id,
            arguments=arguments,
            conversation_id=conversation_id,
            message_id=message_id,
        )

        start_time = datetime.now(UTC)
        try:
            result = await tool.execute(arguments, user_id)
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            completed = await self.execution_repo.complete_execution(
                execution.id,
                result=result,
                execution_time_ms=execution_time_ms,
            )
            logger.info(
                "Tool executed successfully", tool=tool_name, execution_id=str(execution.id)
            )
            return completed

        except Exception as e:
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            completed = await self.execution_repo.complete_execution(
                execution.id,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
            logger.error("Tool execution failed", tool=tool_name, error=str(e))
            return completed

    async def get_execution_history(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[ToolExecution]:
        return await self.execution_repo.get_by_user(user_id, skip, limit)

    async def get_conversation_tools(self, conversation_id: UUID) -> Sequence[ToolExecution]:
        return await self.execution_repo.get_by_conversation(conversation_id)
