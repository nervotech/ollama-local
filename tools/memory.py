import os
import shutil
import tempfile

from .tool_registery import tool


# ============================================================
# GENERIC FILE ACCESS
# ============================================================

def _resolve_path(path: str) -> str:
    """
    Resolve and validate a file path.

    Restrict access to the project's data directory to prevent
    accidental writes to arbitrary system or application files.
    """

    if not isinstance(path, str) or not path.strip():
        raise ValueError("File path must be a non-empty string.")

    base_directory = os.path.abspath("data")
    target_path = os.path.abspath(path)

    # Ensure the requested file is inside the allowed directory.
    if os.path.commonpath([base_directory, target_path]) != base_directory:
        raise ValueError(
            "Access is only allowed to files inside the data directory."
        )

    return target_path


def _replace_file(path: str, content: str) -> bool:
    """
    Safely replace a text file.

    - Validates content.
    - Creates parent directories if necessary.
    - Creates a .bak backup when the file already exists.
    - Writes to a temporary file.
    - Atomically replaces the original file.
    """

    if not isinstance(content, str):
        raise TypeError("File content must be a string.")

    if not content.strip():
        raise ValueError("File content cannot be empty.")

    path = _resolve_path(path)

    directory = os.path.dirname(path)
    filename = os.path.basename(path)

    os.makedirs(directory, exist_ok=True)

    backup_path = path + ".bak"
    temp_path = None

    try:
        # Back up the existing file.
        if os.path.exists(path):
            shutil.copy2(path, backup_path)

        # Write to a temporary file in the same directory.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=f".{filename}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:

            temp_path = temp_file.name
            temp_file.write(content.rstrip() + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())

        # Atomic replacement.
        os.replace(temp_path, path)
        temp_path = None

        return True

    finally:
        # Clean up temporary file if replacement failed.
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ============================================================
# READ FILE
# ============================================================

read_file_description = """
**Tool Name: `read_file`**

Read the complete contents of a text file.

Use this tool to retrieve information stored in files before
modifying or processing them.

Guidelines:

- Provide the path to the file.
- Returns the complete file contents.
- Returns an empty string if the file does not exist.
- Only files inside the allowed data directory can be accessed.

Example paths:

- `data/memory/memory.md`
- `data/knowledge/knowledge.md`
- `data/projects/project.md`
"""


@tool(
    read_file_description,
    {
        "path": {
            "type": "string",
            "description": "The path of the file to read.",
        }
    },
)
def read_file(path: str) -> str:
    """Read the complete contents of a text file."""

    path = _resolve_path(path)

    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    except FileNotFoundError:
        return ""


# ============================================================
# WRITE FILE
# ============================================================

write_file_description = """
**Tool Name: `write_file`**

Safely replace the complete contents of a text file.

This tool REPLACES the existing file contents rather than appending.

Before modifying an existing file:

1. Use `read_file()` to retrieve the current contents.
2. Review and preserve important existing information.
3. Integrate any changes into the complete file contents.
4. Submit the FULL revised file.

Safety behavior:

- Creates parent directories when necessary.
- Creates a `.bak` backup of an existing file.
- Writes through a temporary file.
- Atomically replaces the original file.
- Rejects empty content.
- Only files inside the allowed data directory can be accessed.

Example paths:

- `data/memory/memory.md`
- `data/knowledge/knowledge.md`
- `data/projects/project.md`

Parameters:

- path: The file to write.
- content: The complete replacement content.

Returns:
True if the file was successfully replaced.
"""


@tool(
    write_file_description,
    {
        "path": {
            "type": "string",
            "description": "The path of the file to write.",
        },
        "content": {
            "type": "string",
            "description": (
                "The complete replacement content for the file."
            ),
        },
    },
)
def write_file(path: str, content: str) -> bool:
    """Safely replace the complete contents of a text file."""

    return _replace_file(path, content)