from .tool_registery import tool
import subprocess


@tool(
    "Use this tool to execute shell commands and return the output. Use this "
    "when you need to run system commands, inspect the filesystem, manage "
    "processes, or perform other shell-based tasks. The commands should be always windows cmd commands.",
    {
        "command": {
            "type": "string",
            "description": "The shell command you want to execute. For example, 'ls -la'."
        }
    }
)
def execute_shell_command(command):
    try:
        output = subprocess.check_output(
            command,
            shell=True,
            cwd=".",
            text=True,
            timeout= 30
        )
        return output
    except subprocess.CalledProcessError as error:
        return f"Error: {error}"
    except Exception as error:
        return f"Error executing command: {error}"
