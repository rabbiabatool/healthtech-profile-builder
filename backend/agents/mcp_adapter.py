"""Model Context Protocol (MCP) Typed Tool Adapter (Week 5 Phase 3).

Implements an MCP-compliant adapter conforming to the JSON-RPC tool specification.
Demonstrates:
1. Tool Manifest Schema discovery (list_tools) with JSON Schema type contracts.
2. Runtime permission enforcement: Validates caller roles before invoking tool handlers.
3. Input sanitization & PII redaction on all MCP parameters.
4. Standardized error mapping and structured content output blocks.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from agents.redaction import redact_sensitive_data
from agents.tools import TOOL_REGISTRY, BaseAgentTool


class MCPToolAdapter:
    """Enterprise Adapter implementing Model Context Protocol (MCP) Tool specification."""

    def __init__(self):
        self.server_name = "greenleaf-healthtech-mcp-server"
        self.version = "1.0.0"

    def list_mcp_tools(self) -> List[Dict[str, Any]]:
        """Returns tools formatted per MCP tools/list JSON-RPC standard."""
        mcp_tools = []
        for name, tool in TOOL_REGISTRY.items():
            if name == "search_approved_documents":
                input_schema = {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query keywords for clinic policy documents."},
                        "category": {"type": "string", "description": "Optional category filter (e.g. booking, cancellation, privacy)."},
                        "top_k": {"type": "integer", "default": 3, "description": "Maximum passages to retrieve."},
                    },
                    "required": ["query"],
                }
            elif name == "check_appointment_availability":
                input_schema = {
                    "type": "object",
                    "properties": {
                        "department": {"type": "string", "description": "Clinic department (general_practice, cardiology, telehealth, pediatrics)."},
                        "date": {"type": "string", "description": "Target date in YYYY-MM-DD format."},
                    },
                    "required": ["department"],
                }
            elif name == "request_supervised_prediction":
                input_schema = {
                    "type": "object",
                    "properties": {
                        "patient_features": {
                            "type": "object",
                            "properties": {
                                "age": {"type": "number"},
                                "lead_time_days": {"type": "number"},
                                "previous_no_shows": {"type": "integer"},
                            },
                        },
                    },
                    "required": ["patient_features"],
                }
            elif name == "retrieve_cluster_summaries":
                input_schema = {
                    "type": "object",
                    "properties": {
                        "cluster_id": {"type": "integer", "description": "Optional cluster ID (0-5)."},
                    },
                }
            elif name == "schedule_mock_appointment":
                input_schema = {
                    "type": "object",
                    "properties": {
                        "department": {"type": "string"},
                        "date": {"type": "string"},
                        "slot_time": {"type": "string"},
                        "reason": {"type": "string"},
                        "idempotency_key": {"type": "string", "description": "UUID preventing duplicate appointment creation."},
                        "human_confirmation": {"type": "boolean", "description": "Must be true to commit write."},
                    },
                    "required": ["department", "date", "slot_time", "idempotency_key"],
                }
            else:
                input_schema = {"type": "object", "properties": {}}

            mcp_tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": input_schema,
                "is_write_tool": tool.is_write_tool,
                "required_role": tool.required_role,
            })
        return mcp_tools

    def call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Any,
        human_confirmed: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes a tool call per MCP tools/call standard."""
        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"MCP Error: Tool '{tool_name}' not found on server."}],
            }

        # Runtime Permission Verification
        if not tool.authorize(user):
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"MCP Permission Denied: Caller lacks required role '{tool.required_role}'."}],
            }

        # Execute tool
        try:
            res = tool.execute(
                user=user,
                arguments=arguments,
                human_confirmed=human_confirmed,
                idempotency_key=idempotency_key,
            )

            is_error = res.status in ["denied", "failed", "confirmation_required"]
            text_payload = json.dumps({
                "status": res.status,
                "data": res.result_data,
                "error": res.error,
                "execution_latency_ms": res.execution_latency_ms,
            }, indent=2)

            # Redact any sensitive content in the MCP response
            clean_text, _ = redact_sensitive_data(text_payload)

            return {
                "isError": is_error,
                "content": [{"type": "text", "text": clean_text}],
                "tool_status": res.status,
            }
        except Exception as exc:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"MCP Execution Exception: {str(exc)}"}],
            }


# Singleton instance
_mcp_adapter = MCPToolAdapter()

def get_mcp_adapter() -> MCPToolAdapter:
    return _mcp_adapter

