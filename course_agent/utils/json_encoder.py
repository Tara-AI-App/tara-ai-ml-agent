"""
Custom JSON encoder to handle Pydantic types and other non-serializable objects.
"""
import json
from typing import Any
from pydantic import BaseModel
from pydantic.networks import AnyUrl


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Pydantic types and URLs."""

    def default(self, obj: Any) -> Any:
        """Handle serialization of custom objects."""

        # Handle Pydantic URL types
        if isinstance(obj, AnyUrl):
            return str(obj)

        # Handle other Pydantic models
        if isinstance(obj, BaseModel):
            try:
                # Try Pydantic v2 method first
                if hasattr(obj, 'model_dump'):
                    return obj.model_dump()
                # Fallback to Pydantic v1
                else:
                    return obj.dict()
            except Exception:
                return str(obj)

        # Handle objects with __dict__
        if hasattr(obj, '__dict__'):
            try:
                return {k: self.default(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                       for k, v in obj.__dict__.items()}
            except Exception:
                return str(obj)

        # Handle other types that have string representation
        if hasattr(obj, '__str__'):
            return str(obj)

        # Fallback to default behavior
        return super().default(obj)


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize object to JSON string."""
    return json.dumps(obj, cls=CustomJSONEncoder, **kwargs)


def safe_json_loads(s: str) -> Any:
    """Safely deserialize JSON string to object."""
    return json.loads(s)


def make_json_serializable(obj: Any) -> Any:
    """Convert object to JSON serializable format."""
    encoder = CustomJSONEncoder()

    # Use the encoder's default method to convert the object
    try:
        # Test if object is already serializable
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        # Use custom encoder to convert
        return encoder.default(obj)