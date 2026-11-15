from .tool_registery import tool

@tool("Use this tool to get the current time realted results.", {})
def get_current_time(**args) -> dict:
    from datetime import datetime
    date = datetime.now()
    return {"year": date.strftime("%Y"),
            "month":date.strftime("%m"),
            "day" :date.strftime("%d"),
            "weekday": date.strftime("%A"),
            "hour": date.strftime("%H"),
            "minute": date.strftime("%M"),
            "second": date.strftime("%S")
            }