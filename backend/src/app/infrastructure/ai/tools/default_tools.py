from typing import Any
from uuid import UUID

from app.infrastructure.ai.tools.base import BaseTool, ToolRegistry


class SearchCustomersTool(BaseTool):
    name = "search_customers"
    description = "Search for customers by name, email, or phone number"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query (name, email, or phone)"},
            "limit": {"type": "integer", "description": "Maximum number of results", "default": 10},
        },
        "required": ["query"],
    }
    required_permissions = ["customer:read"]

    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)

        return {
            "customers": [
                {
                    "id": "cust_1",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": "+1234567890",
                },
                {
                    "id": "cust_2",
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "phone": "+1987654321",
                },
            ],
            "total": 2,
        }


class SearchOrdersTool(BaseTool):
    name = "search_orders"
    description = "Search for orders by customer, status, or date range"
    parameters = {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer ID"},
            "status": {"type": "string", "description": "Order status"},
            "date_from": {"type": "string", "description": "Start date (ISO format)"},
            "date_to": {"type": "string", "description": "End date (ISO format)"},
            "limit": {"type": "integer", "description": "Maximum number of results", "default": 10},
        },
    }
    required_permissions = ["order:read"]

    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        return {
            "orders": [
                {
                    "id": "ord_1",
                    "customer_id": "cust_1",
                    "status": "completed",
                    "total": 99.99,
                    "date": "2024-01-15",
                },
                {
                    "id": "ord_2",
                    "customer_id": "cust_1",
                    "status": "pending",
                    "total": 149.99,
                    "date": "2024-01-20",
                },
            ],
            "total": 2,
        }


class SearchProductsTool(BaseTool):
    name = "search_products"
    description = "Search for products by name, category, or SKU"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "category": {"type": "string", "description": "Product category"},
            "in_stock_only": {
                "type": "boolean",
                "description": "Show only in-stock products",
                "default": False,
            },
            "limit": {"type": "integer", "description": "Maximum number of results", "default": 10},
        },
    }
    required_permissions = ["product:read"]

    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        return {
            "products": [
                {
                    "id": "prod_1",
                    "name": "Widget Pro",
                    "category": "Electronics",
                    "price": 49.99,
                    "stock": 100,
                },
                {
                    "id": "prod_2",
                    "name": "Gadget Plus",
                    "category": "Electronics",
                    "price": 79.99,
                    "stock": 50,
                },
            ],
            "total": 2,
        }


class CreateSupportTicketTool(BaseTool):
    name = "create_support_ticket"
    description = "Create a new support ticket"
    parameters = {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer ID"},
            "subject": {"type": "string", "description": "Ticket subject"},
            "description": {"type": "string", "description": "Ticket description"},
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "urgent"],
                "default": "medium",
            },
            "category": {"type": "string", "description": "Ticket category"},
        },
        "required": ["customer_id", "subject", "description"],
    }
    required_permissions = ["ticket:create"]

    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        return {
            "ticket_id": "ticket_123",
            "status": "created",
            "message": "Support ticket created successfully",
        }


class SendEmailTool(BaseTool):
    name = "send_email"
    description = "Send an email to a customer"
    parameters = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body (HTML supported)"},
            "template_id": {"type": "string", "description": "Optional template ID"},
        },
        "required": ["to", "subject", "body"],
    }
    required_permissions = ["email:send"]

    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        return {
            "message_id": "msg_456",
            "status": "sent",
            "message": "Email sent successfully",
        }


class ScheduleAppointmentTool(BaseTool):
    name = "schedule_appointment"
    description = "Schedule an appointment with a customer"
    parameters = {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer ID"},
            "date": {"type": "string", "description": "Appointment date (ISO format)"},
            "duration_minutes": {
                "type": "integer",
                "description": "Duration in minutes",
                "default": 30,
            },
            "type": {"type": "string", "description": "Appointment type"},
            "notes": {"type": "string", "description": "Additional notes"},
        },
        "required": ["customer_id", "date"],
    }
    required_permissions = ["appointment:create"]

    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        return {
            "appointment_id": "appt_789",
            "status": "scheduled",
            "message": "Appointment scheduled successfully",
        }


class SearchFAQsTool(BaseTool):
    name = "search_faqs"
    description = "Search FAQ knowledge base"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "category": {"type": "string", "description": "FAQ category"},
            "limit": {"type": "integer", "description": "Maximum number of results", "default": 5},
        },
        "required": ["query"],
    }
    required_permissions = ["faq:read"]

    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        return {
            "faqs": [
                {
                    "id": "faq_1",
                    "question": "How do I reset my password?",
                    "answer": "Click 'Forgot Password' on the login page...",
                    "category": "Account",
                },
                {
                    "id": "faq_2",
                    "question": "What is your refund policy?",
                    "answer": "We offer 30-day returns...",
                    "category": "Billing",
                },
            ],
            "total": 2,
        }


class CheckInventoryTool(BaseTool):
    name = "check_inventory"
    description = "Check product inventory levels"
    parameters = {
        "type": "object",
        "properties": {
            "product_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Product IDs to check",
            },
            "warehouse_id": {"type": "string", "description": "Optional warehouse ID"},
        },
        "required": ["product_ids"],
    }
    required_permissions = ["inventory:read"]

    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        return {
            "inventory": [
                {"product_id": "prod_1", "available": 100, "reserved": 10, "warehouse": "main"},
                {"product_id": "prod_2", "available": 50, "reserved": 5, "warehouse": "main"},
            ],
        }


class GenerateQuotationTool(BaseTool):
    name = "generate_quotation"
    description = "Generate a price quotation for a customer"
    parameters = {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer ID"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "quantity": {"type": "integer"},
                        "unit_price": {"type": "number"},
                    },
                    "required": ["product_id", "quantity", "unit_price"],
                },
            },
            "valid_until": {
                "type": "string",
                "description": "Quotation validity date (ISO format)",
            },
            "notes": {"type": "string", "description": "Additional notes"},
        },
        "required": ["customer_id", "items"],
    }
    required_permissions = ["quotation:create"]

    async def execute(self, arguments: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        items = arguments.get("items", [])
        total = sum(item["quantity"] * item["unit_price"] for item in items)
        return {
            "quotation_id": "quote_101",
            "total": total,
            "status": "draft",
            "message": "Quotation generated successfully",
        }


def register_default_tools():
    ToolRegistry.register(SearchCustomersTool())
    ToolRegistry.register(SearchOrdersTool())
    ToolRegistry.register(SearchProductsTool())
    ToolRegistry.register(CreateSupportTicketTool())
    ToolRegistry.register(SendEmailTool())
    ToolRegistry.register(ScheduleAppointmentTool())
    ToolRegistry.register(SearchFAQsTool())
    ToolRegistry.register(CheckInventoryTool())
    ToolRegistry.register(GenerateQuotationTool())
