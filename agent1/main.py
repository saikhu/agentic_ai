"""
main.py — run the agent from the command line.

Usage:
  python main.py                    # interactive mode
  python main.py "fix the bug in main.py"
  python main.py --demo             # run a built-in demo task
"""

import sys
import argparse
from agent import run_agent

# ── A small demo codebase for the agent to work on ────────────
DEMO_CODE = '''# buggy_calculator.py
# This file has several bugs. Can you find and fix them all?

def divide(a, b):
    return a / b   # bug: no zero division check

def average(numbers):
    return sum(numbers) / len(numbers)  # bug: crashes on empty list

def celsius_to_fahrenheit(c):
    return c * 9/5 + 32

def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    seq = [0, 1]
    for i in range(2, n):
        seq.append(seq[-2] + seq[-1])  # bug: should be seq[i-1] + seq[i-2]... wait is this right?
    return seq

def count_words(text):
    words = text.split(" ")   # bug: doesn't handle multiple spaces or newlines
    return len(words)

if __name__ == "__main__":
    print(divide(10, 0))       # will crash
    print(average([]))         # will crash
    print(fibonacci(8))
    print(count_words("hello   world"))
'''

DEMO_TESTS = '''# test_calculator.py
import pytest
from buggy_calculator import divide, average, fibonacci, count_words, celsius_to_fahrenheit

def test_divide_normal():
    assert divide(10, 2) == 5.0

def test_divide_by_zero():
    assert divide(10, 0) is None  # or raises, depending on fix

def test_average_normal():
    assert average([1, 2, 3]) == 2.0

def test_average_empty():
    assert average([]) == 0  # should not crash

def test_fibonacci():
    assert fibonacci(8) == [0, 1, 1, 2, 3, 5, 8, 13]

def test_count_words():
    assert count_words("hello   world") == 2
    assert count_words("one\\ntwo\\nthree") == 3

def test_celsius():
    assert celsius_to_fahrenheit(0) == 32.0
    assert celsius_to_fahrenheit(100) == 212.0
'''


def write_demo_files():
    """Create a small buggy project for the agent to fix."""
    import os
    demo_dir = "./demo_project"
    os.makedirs(demo_dir, exist_ok=True)
    with open(f"{demo_dir}/buggy_calculator.py", "w") as f:
        f.write(DEMO_CODE)
    with open(f"{demo_dir}/test_calculator.py", "w") as f:
        f.write(DEMO_TESTS)
    print(f"✓ Demo project created at {demo_dir}/")
    print("  - buggy_calculator.py  ← has 3 bugs")
    print("  - test_calculator.py   ← test suite")
    return demo_dir


def main():
    parser = argparse.ArgumentParser(description="Local coding agent powered by Qwen2.5-Coder via Ollama")
    parser.add_argument("task", nargs="?", help="Task for the agent to perform")
    parser.add_argument("--demo", action="store_true", help="Run a built-in demo: fix bugs in a small Python project")
    parser.add_argument("--max-turns", type=int, default=20, help="Max agent loop iterations (default: 20)")
    args = parser.parse_args()

    if args.demo:
        demo_dir = write_demo_files()
        task = (
            f"I have a Python project at {demo_dir}/. "
            "It has a file called buggy_calculator.py with several bugs, "
            "and a test file called test_calculator.py. "
            "Please: 1) Read both files, 2) identify all bugs, "
            "3) fix them, 4) run the tests to verify everything passes."
        )
        run_agent(task, max_turns=args.max_turns)

    elif args.task:
        run_agent(args.task, max_turns=args.max_turns)

    else:
        # Interactive REPL mode
        print("\n🤖 Coding Agent — powered by Qwen2.5-Coder:32b via Ollama")
        print("   Type your task, or 'quit' to exit.\n")
        while True:
            try:
                task = input("You: ").strip()
                if task.lower() in ("quit", "exit", "q"):
                    break
                if task:
                    run_agent(task, max_turns=args.max_turns)
            except (KeyboardInterrupt, EOFError):
                print("\nBye!")
                break


if __name__ == "__main__":
    main()