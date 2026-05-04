# Local Coding Agent

A minimal but complete AI coding agent built from scratch.
Powered by **Qwen2.5-Coder:32b** running locally via **Ollama**.

## Architecture

```
main.py          ← CLI entry point, demo tasks
agent.py         ← the agent loop (while True)
tools.py         ← tool implementations + JSON schemas
```

The agent loop in plain English:
1. Send [system prompt + conversation history + tools] to Ollama
2. If model calls a tool → run it in Python → append result → go to 1
3. If model gives a text answer → print it → done

## Setup

```bash
# Install Ollama (already done if you're here)
brew install ollama

# Pull the model (~20GB, one-time)
ollama pull qwen2.5-coder:32b

# Start Ollama server (in a separate terminal)
OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 ollama serve

# Install Python dependency
pip install openai
```

## Usage

```bash
# Interactive REPL
python main.py

# Single task
python main.py "list what's in the current directory"
python main.py "read main.py and explain what it does"
python main.py "create a Python script that generates a Fibonacci sequence"

# Built-in demo: find and fix bugs, run tests
python main.py --demo
```

## Available Tools

| Tool           | What it does                                 |
|----------------|----------------------------------------------|
| `read_file`    | Read a file with line numbers                |
| `write_file`   | Write/overwrite a file                       |
| `list_dir`     | List directory contents                      |
| `run_command`  | Run shell commands (python, pytest, git...)  |
| `search_code`  | Grep for a pattern across files              |

## Key concepts

- **No framework** — the loop in `agent.py` is ~60 lines of pure Python
- **Stateless model** — every call includes full conversation history
- **Tools = JSON schema + Python function** — the model picks the tool,
  your code runs it
- **Context window** — all messages stay in memory for the session;
  for long sessions you'd want to summarise old turns

## Adding your own tools

1. Write the Python function in `tools.py`
2. Add it to `TOOL_FUNCTIONS` dict
3. Add its JSON schema to the `TOOLS` list
4. The model will automatically discover and use it