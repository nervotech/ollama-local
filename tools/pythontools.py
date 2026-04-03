from .tool_registery import tool

@tool("Use this tool to execute Python code and return the output. Only use this when required to check the correctness of the code. If not, ignore this tool.", 
    {"code": {
                "type": "string",
                "description": "The Python code you want to execute. For example, 'print(2 + 2)'."
            }})
def execute_python_code(code):
    import sys
    import io
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    try:
        exec(code)
        output = redirected_output.getvalue()
    except Exception as e:
        output = f"Error executing code: {e}"
    finally:
        sys.stdout = old_stdout
    return output