import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUFF = ROOT / ".venv" / "Scripts" / "ruff.exe"

data = json.load(sys.stdin)
tool_input = data.get("tool_input") or {}
tool_response = data.get("tool_response") or {}
file_path = tool_input.get("file_path") or tool_response.get("filePath") or ""

if file_path.endswith(".py") and RUFF.exists():
    subprocess.run([str(RUFF), "check", "--fix", "--quiet", file_path])
    subprocess.run([str(RUFF), "format", "--quiet", file_path])
