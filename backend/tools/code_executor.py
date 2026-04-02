"""Safe Python code execution tool using subprocess isolation."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
import tempfile
import textwrap
from langchain_core.tools import tool
from config import settings

# Forbidden patterns for security
FORBIDDEN_PATTERNS = [
    "import os",
    "import sys",
    "import subprocess",
    "import socket",
    "__import__",
    "open(",
    "exec(",
    "eval(",
    "compile(",
    "globals(",
    "locals(",
    "getattr(",
    "setattr(",
    "delattr(",
    "importlib",
    "shutil",
    "pathlib",
    "requests",
    "httpx",
    "urllib",
    "ctypes",
    "multiprocessing",
    "threading",
    "pickle",
]


def _is_safe_code(code: str) -> tuple[bool, str]:
    """Basic security check for code before execution."""
    code_lower = code.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in code_lower:
            return False, f"Forbidden pattern detected: '{pattern}'"
    return True, ""


@tool
def run_python_code(code: str) -> str:
    """
    Execute Python code safely in an isolated subprocess with a time limit.
    Use for data analysis, algorithms, string processing, list comprehensions,
    math computations, or demonstrating Python concepts.

    LIMITATIONS: No file I/O, no network access, no OS operations.
    Available modules: math, json, re, datetime, collections, itertools, functools, random, statistics.

    Args:
        code: Python code to execute (multi-line supported)

    Returns:
        Standard output from the code execution, or error message
    """
    is_safe, reason = _is_safe_code(code)
    if not is_safe:
        return f"Code rejected for security: {reason}"

    # Wrap code with safe imports pre-loaded
    safe_preamble = textwrap.dedent("""
        import math
        import json
        import re
        import datetime
        import collections
        import itertools
        import functools
        import random
        import statistics
        from math import *
        from collections import Counter, defaultdict, deque, OrderedDict
        from itertools import *
    """)

    full_code = safe_preamble + "\n" + code

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(full_code)
            tmp_path = f.name

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=settings.CODE_EXECUTION_TIMEOUT,
            env={"PATH": os.environ.get("PATH", "")},  # Minimal env
        )

        os.unlink(tmp_path)

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode == 0:
            if stdout:
                # Truncate very long output
                if len(stdout) > 3000:
                    stdout = stdout[:3000] + "\n[Output truncated]"
                return f"Output:\n{stdout}"
            return "Code executed successfully (no output)"
        else:
            # Clean up Python error traceback for readability
            if "Error" in stderr:
                lines = stderr.split("\n")
                error_lines = [l for l in lines if "Error" in l or "    " in l]
                return f"Error:\n{chr(10).join(error_lines[-5:])}"
            return f"Execution error:\n{stderr}"

    except subprocess.TimeoutExpired:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return f"Timeout: Code exceeded {settings.CODE_EXECUTION_TIMEOUT}s limit"
    except Exception as e:
        return f"Execution failed: {str(e)}"
