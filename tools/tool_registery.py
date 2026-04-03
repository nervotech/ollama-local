# 
from typing import Callable, Dict

TOOLS_REGISTRY: Dict[str, Dict] = {}

def tool(desc: str, args: Dict):
    def decorator(func: Callable) -> Callable:
        TOOLS_REGISTRY[func.__name__] = {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": desc,
                "parameters": {
                    "type": "object",
                    "properties": args,
                    "required": []
                }
            },
            "call": func
        }
        return func
    return decorator