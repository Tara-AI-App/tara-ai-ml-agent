"""
Serializable MCP wrapper to handle JSON serialization issues.
"""
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from google.adk.tools.mcp_tool import McpToolset

from ..utils.logger import logger


class SerializableMCPWrapper:
    """Wrapper for MCP tools that ensures JSON serializable responses."""

    def __init__(self, mcp_toolset: McpToolset):
        self._toolset = mcp_toolset
        self._tools = {}

        # Extract and wrap all tools from the toolset
        if hasattr(mcp_toolset, '_tools') and mcp_toolset._tools:
            for tool_name, tool in mcp_toolset._tools.items():
                self._tools[tool_name] = self._wrap_tool(tool, tool_name)

    def _wrap_tool(self, tool, tool_name: str):
        """Wrap a tool to ensure JSON serializable responses."""
        def wrapped_tool(*args, **kwargs):
            try:
                # Call the original tool
                result = tool(*args, **kwargs)

                # Ensure the result is JSON serializable
                serializable_result = self._make_json_serializable(result)

                logger.debug(f"MCP tool {tool_name} response serialized successfully")
                return serializable_result

            except Exception as e:
                logger.error(f"MCP tool {tool_name} failed: {e}")
                return {
                    "error": f"Tool {tool_name} failed: {str(e)}",
                    "tool_name": tool_name
                }

        # Preserve tool metadata
        if hasattr(tool, '__name__'):
            wrapped_tool.__name__ = tool.__name__
        if hasattr(tool, '__doc__'):
            wrapped_tool.__doc__ = tool.__doc__

        return wrapped_tool

    def _make_json_serializable(self, obj: Any) -> Any:
        """Recursively convert objects to JSON serializable format."""
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}

        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]

        elif isinstance(obj, BaseModel):
            # Handle Pydantic models
            try:
                # Try to use model_dump if available (Pydantic v2)
                if hasattr(obj, 'model_dump'):
                    data = obj.model_dump()
                else:
                    # Fallback to dict() for Pydantic v1
                    data = obj.dict()
                return self._make_json_serializable(data)
            except Exception:
                # If model serialization fails, convert to string
                return str(obj)

        elif hasattr(obj, '__dict__'):
            # Handle objects with __dict__
            try:
                return self._make_json_serializable(obj.__dict__)
            except Exception:
                return str(obj)

        elif hasattr(obj, '__str__'):
            # Convert anything with __str__ to string
            return str(obj)

        else:
            # Last resort - try JSON serialization test
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)

    def get_tool(self, tool_name: str):
        """Get a wrapped tool by name."""
        return self._tools.get(tool_name)

    def __getattr__(self, name: str):
        """Proxy attribute access to wrapped tools or original toolset."""
        if name in self._tools:
            return self._tools[name]

        # Fallback to original toolset for other attributes
        attr = getattr(self._toolset, name)

        # If it's a callable tool, wrap it
        if callable(attr) and not name.startswith('_'):
            return self._wrap_tool(attr, name)

        return attr

    @property
    def tools(self):
        """Return the wrapped tools dictionary."""
        return self._tools


def create_serializable_mcp_wrapper(mcp_toolset: McpToolset) -> Optional[SerializableMCPWrapper]:
    """Create a serializable wrapper for MCP toolset."""
    if not mcp_toolset:
        return None

    try:
        wrapper = SerializableMCPWrapper(mcp_toolset)
        logger.info("Created serializable MCP wrapper")
        return wrapper
    except Exception as e:
        logger.error(f"Failed to create serializable MCP wrapper: {e}")
        return None