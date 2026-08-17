import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class ToolCategory(str, enum.Enum):
    CUSTOMER = "customer"
    ORDER = "order"
    PRODUCT = "product"
    TICKET = "ticket"
    EMAIL = "email"
    APPOINTMENT = "appointment"
    FAQ = "faq"
    INVENTORY = "inventory"
    QUOTATION = "quotation"
    CUSTOM = "custom"


class ToolStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class AITool(Base):
    __tablename__ = "ai_tools"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ToolCategory] = mapped_column(
        Enum(ToolCategory, name="tool_category", create_constraint=True),
        nullable=False,
    )
    status: Mapped[ToolStatus] = mapped_column(
        Enum(ToolStatus, name="tool_status", create_constraint=True),
        default=ToolStatus.ACTIVE,
        nullable=False,
    )
    function_schema: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    required_permissions: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    implementation: Mapped[str] = mapped_column(String(255), nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(default=30, nullable=False)
    rate_limit: Mapped[int | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AITool(id={self.id}, name={self.name}, category={self.category})>"


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tool_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ai_tools.id"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    arguments: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ToolExecution(id={self.id}, tool_id={self.tool_id}, status={self.status})>"
