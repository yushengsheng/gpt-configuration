#!/usr/bin/env python3
"""Bounded continuation hook for Codex model-capacity failures."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


DEFAULT_MAX_ATTEMPTS = 8
DEFAULT_DELAYS = (5, 15, 30, 60)
STATE_TTL_SECONDS = 60 * 60
MAX_STATE_ENTRIES = 64
TRANSCRIPT_TAIL_BYTES = 64 * 1024

CAPACITY_PATTERNS = (
    re.compile(r"\bselected\s+model\s+is\s+at\s+capacity\b", re.I),
    re.compile(r"\b(?:the\s+)?model\s+is\s+(?:currently\s+)?at\s+capacity\b", re.I),
    re.compile(r"\bmodel\s+capacity\s+(?:has\s+been\s+)?reached\b", re.I),
    re.compile(r"\bcapacity\s+limit\s+(?:has\s+been\s+)?reached\b", re.I),
    re.compile(r"模型(?:已|目前)?(?:满载|容量不足|达到容量)", re.I),
)


def _positive_int(value: str | None, default: int, maximum: int) -> int:
    try:
        parsed = int(value or "")
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def _nonnegative_int(value: object, default: int, maximum: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    return max(0, min(parsed, maximum))


def _delays() -> tuple[int, ...]:
    raw = os.environ.get("CODEX_AUTO_RETRY_DELAYS", "")
    if not raw.strip():
        return DEFAULT_DELAYS
    values: list[int] = []
    for item in raw.split(","):
        try:
            values.append(max(0, min(int(item.strip()), 300)))
        except ValueError:
            continue
    return tuple(values) or DEFAULT_DELAYS


def _state_path() -> Path | None:
    configured = os.environ.get("CODEX_AUTO_RETRY_STATE_DIR") or os.environ.get("PLUGIN_DATA")
    if not configured:
        return None
    return Path(configured).expanduser() / "auto-retry-state.json"


def _load_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {"sessions": {}}
    if not isinstance(data, dict) or not isinstance(data.get("sessions"), dict):
        return {"sessions": {}}
    now = time.time()
    sessions = {
        key: value
        for key, value in data["sessions"].items()
        if isinstance(value, dict)
        and isinstance(value.get("updated_at"), (int, float))
        and now - float(value["updated_at"]) <= STATE_TTL_SECONDS
    }
    return {"sessions": sessions}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sessions = state.setdefault("sessions", {})
    if len(sessions) > MAX_STATE_ENTRIES:
        oldest = sorted(
            sessions.items(), key=lambda item: float(item[1].get("updated_at", 0))
        )[: len(sessions) - MAX_STATE_ENTRIES]
        for key, _ in oldest:
            sessions.pop(key, None)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(state, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _payload() -> dict[str, Any] | None:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def _text_for_detection(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    message = payload.get("last_assistant_message")
    if isinstance(message, str):
        parts.append(message)
    transcript = payload.get("transcript_path")
    if isinstance(transcript, str) and transcript:
        try:
            with Path(transcript).open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                handle.seek(max(0, handle.tell() - TRANSCRIPT_TAIL_BYTES))
                parts.append(handle.read().decode("utf-8", errors="replace"))
        except OSError:
            pass
    return "\n".join(parts)


def _is_capacity_error(text: str) -> bool:
    return any(pattern.search(text) for pattern in CAPACITY_PATTERNS)


def _emit(value: dict[str, Any]) -> None:
    json.dump(value, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


def _session_key(payload: dict[str, Any]) -> str:
    session_id = str(payload.get("session_id") or "unknown-session")
    turn_id = str(payload.get("turn_id") or "unknown-turn")
    return f"{session_id}:{turn_id}"


def _record_model_request(payload: dict[str, Any]) -> int:
    """Remember a failed model request for Stop, whose message can be empty."""
    state_path = _state_path()
    if state_path is None:
        return 0
    state = _load_state(state_path)
    sessions = state["sessions"]
    key = _session_key(payload)
    status = str(payload.get("status") or "").lower()
    error = payload.get("error")
    error_text = error if isinstance(error, str) else ""

    if status == "failed" and _is_capacity_error(error_text):
        previous = sessions.get(key, {})
        attempts = _nonnegative_int(previous.get("attempts", 0), 0, 33)
        sessions[key] = {
            "attempts": attempts,
            "capacity_error": True,
            "updated_at": time.time(),
        }
        _save_state(state_path, state)
    elif status in {"completed", "cancelled"} and key in sessions:
        sessions.pop(key, None)
        _save_state(state_path, state)
    return 0


def main() -> int:
    payload = _payload()
    if not payload:
        return 0
    event = payload.get("hook_event_name")
    if event == "PostModelRequest":
        return _record_model_request(payload)
    if event not in (None, "Stop"):
        return 0

    state_path = _state_path()
    if state_path is None:
        _emit({"systemMessage": "自动重试未启用：Codex 未提供 PLUGIN_DATA。"})
        return 0

    state = _load_state(state_path)
    sessions = state["sessions"]
    key = _session_key(payload)

    previous = sessions.get(key, {})
    last_message = payload.get("last_assistant_message")
    if isinstance(last_message, str) and last_message.strip():
        detected = _is_capacity_error(last_message)
    else:
        detected = _is_capacity_error(_text_for_detection(payload)) or bool(
            previous.get("capacity_error")
        )
    if not detected:
        if key in sessions:
            sessions.pop(key, None)
            _save_state(state_path, state)
        return 0

    max_attempts = _positive_int(
        os.environ.get("CODEX_AUTO_RETRY_MAX_ATTEMPTS"), DEFAULT_MAX_ATTEMPTS, 32
    )
    attempts = _nonnegative_int(previous.get("attempts", 0), 0, max_attempts + 1)

    # A continuation can re-enter Stop with stop_hook_active=true. Only our
    # own bounded chain may continue; this avoids hijacking another hook's loop.
    if payload.get("stop_hook_active") and attempts == 0:
        _emit({"systemMessage": "检测到已有 Stop Hook 正在继续，本插件不重复接管。"})
        return 0

    if attempts >= max_attempts:
        _emit({
            "systemMessage": (
                f"模型容量错误已连续重试 {max_attempts} 次，已暂停自动继续；请稍后手动重试。"
            )
        })
        return 0

    attempts += 1
    delay_values = _delays()
    delay = delay_values[min(attempts - 1, len(delay_values) - 1)]
    sessions[key] = {
        "attempts": attempts,
        "capacity_error": True,
        "updated_at": time.time(),
    }
    _save_state(state_path, state)

    if os.environ.get("CODEX_AUTO_RETRY_DISABLE_SLEEP") not in {"1", "true", "yes"}:
        time.sleep(delay)

    _emit({
        "decision": "block",
        "reason": (
            "检测到上次请求因模型容量不足而停止。"
            f"已等待 {delay} 秒，请继续执行刚才未完成的任务，"
            f"不要重复已经完成的步骤（自动重试 {attempts}/{max_attempts}）。"
        ),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
