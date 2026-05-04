"""
agent.py — the core agent loop.

This is the "while True" loop from the explainer, with some
quality-of-life additions: coloured output, turn tracking, and
a max_turns safety limit so a buggy model can't loop forever.
"""

import json
from openai import OpenAI
from tools import TOOLS, run_tool

# ── ANSI colours for terminal readability ──────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
DIM    = "\033[2m"

def c(text, colour): return f"{colour}{text}{RESET}"

# ── Ollama client (OpenAI-compatible endpoint) ─────────────────
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Ollama ignores this but the library requires it
)

MODEL = "qwen2.5-coder:32b"

SYSTEM_PROMPT = """You are an expert coding assistant running locally on the user's machine.

You have access to tools that let you read files, write files, search code, list directories, 
and run shell commands. Use them proactively — don't ask the user for information you can 
discover yourself with a tool.

When helping with code:
1. First explore the codebase with list_dir and read_file to understand context
2. Make targeted, minimal changes unless a full rewrite is explicitly requested
3. Always run the code after changes to verify it works
4. Explain what you did and why after completing the task

Be concise in your thinking but thorough in your actions."""


# ── Main agent loop ────────────────────────────────────────────

def run_agent(
    user_message: str,
    max_turns: int = 20,
    verbose: bool = True,
) -> str:
    """
    Run the agent loop until the model gives a final answer
    or max_turns is reached.

    Returns the final text response.
    """

    # ── Build initial message history ─────────────────────────
    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_message},
    ]

    if verbose:
        print(f"\n{c('━' * 60, DIM)}")
        print(f"{c('USER', BOLD)}: {user_message}")
        print(f"{c('━' * 60, DIM)}\n")

    # ── The loop ───────────────────────────────────────────────
    for turn in range(1, max_turns + 1):

        if verbose:
            print(c(f"[Turn {turn}] Thinking...", DIM))

        # Call the model
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",   # model decides when to use tools
            temperature=0.2,      # low temp for coding tasks
        )

        message = response.choices[0].message

        # Append the assistant's response to history
        # (we must pass the raw object back in subsequent calls)
        messages.append(message)

        # ── Case 1: Model wants to use a tool ─────────────────
        if message.tool_calls:
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                if verbose:
                    args_preview = json.dumps(args)[:80]
                    print(f"  {c('🔧 Tool call:', YELLOW)} {c(name, BOLD)}({args_preview})")

                # ← This is where YOUR code runs the tool
                result = run_tool(name, args)

                if verbose:
                    preview = str(result).replace("\n", " ")[:120]
                    print(f"  {c('→ Result:', GREEN)} {preview}")
                    print()

                # Feed the result back into message history
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      str(result),
                })

            # Loop again — model may call more tools or give final answer
            continue

        # ── Case 2: No tool call = final text answer ───────────
        final = message.content or ""

        if verbose:
            print(f"\n{c('━' * 60, DIM)}")
            print(f"{c('AGENT', BOLD+CYAN)}: {final}")
            print(f"{c('━' * 60, DIM)}\n")
            print(c(f"Completed in {turn} turn(s)  |  {len(messages)} messages in context", DIM))

        return final

    # ── Safety exit ────────────────────────────────────────────
    warning = f"[Agent stopped: reached max_turns={max_turns}]"
    print(c(warning, RED))
    return warning