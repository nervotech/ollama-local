from .tool_registery import tool

@tool("Use this tool to get the current time", {})
def get_current_time(**args) -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")