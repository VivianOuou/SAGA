"""JSONL decision log with credential redaction."""

import json
import re
from pathlib import Path
from typing import Any, Dict


_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-*]{6,}"),           # OpenAI / Anthropic style keys
    re.compile(r"AKIA[0-9A-Z]{12,}"),                # AWS access key ids
    re.compile(r"(?i)(api[_-]?key|secret|token|password)(\"?\s*[:=]\s*\"?)[^\s\",}]{6,}"),
]
_SECRET_KEYS = re.compile(r"(?i)(api[_-]?key|secret|password|credential|access[_-]?key|token$)")


def redact(value: Any) -> Any:
    if isinstance(value, str):
        out = value
        for pattern in _SECRET_PATTERNS[:2]:
            out = pattern.sub("[REDACTED]", out)
        out = _SECRET_PATTERNS[2].sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", out)
        return out
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if isinstance(k, str) and _SECRET_KEYS.search(k) else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


class DecisionLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: Dict[str, Any]) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(redact(record), default=str) + "\n")
