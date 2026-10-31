from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "hooks" / "auto_retry.py"


class AutoRetryHookTests(unittest.TestCase):
    def run_hook(self, payload: dict, state_dir: Path, **extra_env: str) -> dict | None:
        env = os.environ.copy()
        env.update(
            {
                "PLUGIN_DATA": str(state_dir),
                "CODEX_AUTO_RETRY_DISABLE_SLEEP": "1",
                "CODEX_AUTO_RETRY_MAX_ATTEMPTS": "2",
            }
        )
        env.update(extra_env)
        result = subprocess.run(
            ["python3", str(SCRIPT)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            check=True,
        )
        return json.loads(result.stdout) if result.stdout.strip() else None

    def payload(self, message: str | None, **extra: object) -> dict:
        value: dict[str, object] = {
            "hook_event_name": "Stop",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "stop_hook_active": False,
            "last_assistant_message": message,
            "transcript_path": None,
        }
        value.update(extra)
        return value

    def model_request_payload(self, status: str, error: str | None) -> dict:
        return {
            "hook_event_name": "PostModelRequest",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "status": status,
            "error": error,
            "transcript_path": None,
        }

    def test_capacity_message_requests_bounded_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            result = self.run_hook(
                self.payload("Selected model is at capacity"), state_dir
            )
            self.assertEqual(result["decision"], "block")
            self.assertIn("1/2", result["reason"])

            result = self.run_hook(
                self.payload("Selected model is at capacity", stop_hook_active=True), state_dir
            )
            self.assertEqual(result["decision"], "block")
            self.assertIn("2/2", result["reason"])

    def test_maximum_attempts_stop_the_loop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            for active in (False, True):
                self.run_hook(
                    self.payload("Selected model is at capacity", stop_hook_active=active),
                    state_dir,
                )
            result = self.run_hook(
                self.payload("Selected model is at capacity", stop_hook_active=True), state_dir
            )
            self.assertNotIn("decision", result)
            self.assertIn("暂停自动继续", result["systemMessage"])

    def test_non_capacity_stop_clears_session_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            self.run_hook(self.payload("Selected model is at capacity"), state_dir)
            self.assertIsNone(self.run_hook(self.payload("任务已完成"), state_dir))
            result = self.run_hook(
                self.payload("The selected model is at capacity"), state_dir
            )
            self.assertIn("1/2", result["reason"])

    def test_transcript_is_checked_when_message_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            transcript = state_dir / "rollout.jsonl"
            transcript.write_text("error: model is currently at capacity\n", encoding="utf-8")
            result = self.run_hook(
                self.payload(None, transcript_path=str(transcript)), state_dir
            )
            self.assertEqual(result["decision"], "block")

    def test_failed_model_request_marks_capacity_for_stop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            self.assertIsNone(
                self.run_hook(
                    self.model_request_payload(
                        "failed", "Selected model is at capacity. Please try a different model."
                    ),
                    state_dir,
                )
            )
            result = self.run_hook(self.payload(None), state_dir)
            self.assertEqual(result["decision"], "block")
            self.assertIn("1/2", result["reason"])

    def test_successful_model_request_clears_capacity_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            self.run_hook(
                self.model_request_payload("failed", "model is currently at capacity"), state_dir
            )
            self.assertIsNone(
                self.run_hook(self.model_request_payload("completed", None), state_dir)
            )
            result = self.run_hook(self.payload("任务已完成"), state_dir)
            self.assertIsNone(result)

    def test_malformed_input_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env = os.environ.copy()
            env["PLUGIN_DATA"] = directory
            result = subprocess.run(
                ["python3", str(SCRIPT)],
                input="not-json",
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
