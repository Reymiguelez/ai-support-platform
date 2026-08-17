from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseTool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]
    required_permissions: list[str] = []

    @abstractmethod
    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        pass

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    _tools: dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        cls._tools[tool.name] = tool
        logger.info("Tool registered", tool=tool.name)

    @classmethod
    def get(cls, name: str) -> BaseTool | None:
        return cls._tools.get(name)

    @classmethod
    def get_all(cls) -> list[BaseTool]:
        return list(cls._tools.values())

    @classmethod
    def get_by_category(cls, category: str) -> list[BaseTool]:
        return [tool for tool in cls._tools.values() if getattr(tool, "category", "") == category]

    @classmethod
    def get_schemas(cls) -> list[dict[str, Any]]:
        return [tool.get_schema() for tool in cls._tools.values()]

    @classmethod
    def get_schemas_by_permissions(cls, user_permissions: list[str]) -> list[dict[str, Any]]:
        return [
            tool.get_schema()
            for tool in cls._tools.values()
            if not tool.required_permissions
            or any(p in user_permissions for p in tool.required_permissions)
        ]
