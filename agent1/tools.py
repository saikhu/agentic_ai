"""
tools.py — every tool the agent can call.

Two things live here for each tool:
  1. A JSON schema (tells the LLM what the tool is and what args it takes)
  2. A Python function (what actually runs when the LLM calls it)
"""

import subprocess
import os
import glob

# ─────────────────────────────────────────────
# Tool implementations (real Python code)
# ─────────────────────────────────────────────

def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    try:
        with open(path, "r") as f:
            content = f.read()
        lines = content.splitlines()
        # Add line numbers so the model can reference them precisely
        numbered = "\n".join(f"{i+1:4} | {line}" for i, line in enumerate(lines))
        return f"File: {path} ({len(lines)} lines)\n\n{numbered}"
    except FileNotFoundError:
        return f"Error: file '{path}' not found."
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file, creating directories if needed."""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        lines = content.count("\n") + 1
        return f"✓ Written {lines} lines to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def list_dir(path: str = ".") -> str:
    """List files and directories at the given path."""
    try:
        entries = sorted(os.listdir(path))
        result = []
        for entry in entries:
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                result.append(f"  📁 {entry}/")
            else:
                size = os.path.getsize(full)
                result.append(f"  📄 {entry} ({size:,} bytes)")
        return f"Contents of '{path}':\n" + "\n".join(result) if result else f"'{path}' is empty."
    except Exception as e:
        return f"Error listing directory: {e}"


def run_command(command: str, working_dir: str = ".") -> str:
    """
    Run a shell command and return stdout + stderr.
    Blocked commands: rm -rf, sudo, curl/wget (safety guardrail).
    """
    # Simple safety guardrail — refuse destructive or network commands
    blocked = ["rm -rf", "sudo", "curl ", "wget ", "dd if", "> /dev/"]
    for b in blocked:
        if b in command:
            return f"Blocked: '{b}' is not allowed for safety reasons."

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=working_dir,
        )
        output = result.stdout + result.stderr
        if not output.strip():
            return f"Command exited with code {result.returncode} (no output)"
        # Cap output so we don't blow out context window
        if len(output) > 3000:
            output = output[:3000] + "\n... (truncated)"
        return output
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30 seconds."
    except Exception as e:
        return f"Error running command: {e}"


def search_code(pattern: str, path: str = ".", extension: str = "py") -> str:
    """
    Search for a pattern across all files with the given extension.
    Returns matching lines with file name and line number.
    """
    matches = []
    glob_pattern = os.path.join(path, f"**/*.{extension}")
    files = glob.glob(glob_pattern, recursive=True)

    for filepath in files:
        try:
            with open(filepath, "r") as f:
                for i, line in enumerate(f, 1):
                    if pattern.lower() in line.lower():
                        matches.append(f"{filepath}:{i}: {line.rstrip()}")
        except Exception:
            continue

    if not matches:
        return f"No matches for '{pattern}' in *.{extension} files under '{path}'"
    return f"Found {len(matches)} match(es) for '{pattern}':\n\n" + "\n".join(matches[:50])


# ─────────────────────────────────────────────
# Tool dispatcher — called by the agent loop
# ─────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "read_file":    lambda args: read_file(**args),
    "write_file":   lambda args: write_file(**args),
    "list_dir":     lambda args: list_dir(**args),
    "run_command":  lambda args: run_command(**args),
    "search_code":  lambda args: search_code(**args),
}

def run_tool(name: str, args: dict) -> str:
    """Dispatch a tool call by name."""
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return f"Unknown tool: '{name}'"
    try:
        return fn(args)
    except TypeError as e:
        return f"Tool '{name}' called with wrong args: {e}"


# ─────────────────────────────────────────────
# JSON schemas — what the LLM sees
# These describe each tool so the model knows
# when and how to call them.
# ─────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Returns content with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read, e.g. 'src/main.py'"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates the file and any parent directories if they don't exist. Overwrites existing content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to write to, e.g. 'src/utils.py'"
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file content to write"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and folders in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list. Defaults to current directory.",
                        "default": "."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command and return output. Use for: running Python files, running tests (pytest), checking git status, installing packages, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to run, e.g. 'python main.py' or 'pytest tests/'"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Directory to run the command in. Defaults to current directory.",
                        "default": "."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a string/pattern across all files of a given type. Useful for finding where a function is defined or used.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text to search for"
                    },
                    "path": {
                        "type": "string",
                        "description": "Root directory to search in",
                        "default": "."
                    },
                    "extension": {
                        "type": "string",
                        "description": "File extension to search (without dot), e.g. 'py', 'js', 'ts'",
                        "default": "py"
                    }
                },
                "required": ["pattern"]
            }
        }
    }
]