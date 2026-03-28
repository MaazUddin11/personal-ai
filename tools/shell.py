import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional

ALLOWED_DIR = Path(os.getenv("AGENT_WORKSPACE", os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace"))).resolve()

BLOCKED_COMMANDS = {
    "rm",
    "sudo",
    "chmod",
    "chown",
    "ssh",
    "scp",
    "mv",
}

BLOCKED_TOKENS = {
    "&&",
    ";",
    "|",
    ">",
    ">>",
    "~",
}


def is_path_token(token: str) -> bool:
    if token.startswith("/"):
        return True
    if token.startswith("."):
        return True
    return "/" in token


def path_is_allowed(token: str) -> bool:
    candidate = Path(token).expanduser()

    if not candidate.is_absolute():
        candidate = (ALLOWED_DIR / candidate).resolve()
    else:
        candidate = candidate.resolve()

    try:
        candidate.relative_to(ALLOWED_DIR)
        return True
    except ValueError:
        return False


def validate_command(cmd: str) -> Optional[str]:
    try:
        parts = shlex.split(cmd)
    except ValueError as e:
        return f"Invalid command syntax: {e}"

    if not parts:
        return "No command provided."

    command_name = parts[0]
    if command_name in BLOCKED_COMMANDS:
        return f"Blocked command for safety: {command_name}"

    for token in parts:
        if token in BLOCKED_TOKENS:
            return f"Blocked shell feature for safety: {token}"
        if any(op in token for op in ["&&", ";", "|", ">", ">>"]):
            return f"Blocked shell feature for safety: {token}"

    for token in parts[1:]:
        if is_path_token(token):
            if not path_is_allowed(token):
                return f"Blocked path outside workspace: {token}"

    return None


def run_command(cmd: str) -> str:
    validation_error = validate_command(cmd)
    if validation_error:
        return validation_error

    try:
        parts = shlex.split(cmd)

        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            cwd=str(ALLOWED_DIR),
            timeout=15,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if stdout and stderr:
            return f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
        if stdout:
            return stdout
        if stderr:
            return f"STDERR:\n{stderr}"

        return "Command completed with no output."

    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Command failed: {e}"