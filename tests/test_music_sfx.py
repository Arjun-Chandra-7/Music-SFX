from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from music_sfx.engine import AudioEngine, build_filters, validate_values
from music_sfx.policy import evaluate
from music_sfx.presets import preset


class PolicyTests(unittest.TestCase):
    def test_unknown_rights_requires_approval_but_allows_review_render(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.wav"
            source.touch()
            decision = evaluate(input_path=source, output_path=Path(temp) / "new.wav", rights="unknown", overwrite=False)
            self.assertTrue(decision.allowed)
            self.assertEqual(decision.authority, "approval_required")

    def test_source_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.wav"
            source.touch()
            decision = evaluate(input_path=source, output_path=source, rights="owned", overwrite=True)
            self.assertFalse(decision.allowed)
            self.assertEqual(decision.authority, "forbidden")


class EngineTests(unittest.TestCase):
    def test_parameter_range_is_enforced(self):
        values = preset("clean_master")["values"]
        values["width"] = 201
        with self.assertRaisesRegex(ValueError, "width"):
            validate_values(values)

    def test_filter_is_deterministic_and_limited(self):
        values = validate_values(preset("shorts_punch")["values"])
        first = build_filters(values)
        self.assertEqual(first, build_filters(values))
        self.assertIn("acompressor", first)
        self.assertIn("alimiter", first)
        self.assertTrue(first.endswith("aresample=48000"))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
    def test_real_render_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / "tone.wav", root / "master.wav"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                "sine=frequency=440:duration=0.25", "-c:a", "pcm_s16le", str(source),
            ], check=True)
            engine = AudioEngine(root / "data")
            job = engine.process({
                "input": str(source), "output": str(target), "preset": "clean_master",
                "rights": "owned", "actor": "test-suite", "intent": "render verification",
            })
            self.assertEqual(job["status"], "completed", job.get("error"))
            self.assertTrue(target.is_file())
            self.assertEqual(len(job["source"]["sha256"]), 64)
            self.assertEqual(job["result"]["metadata"]["sample_rate"], 48000)
            events = [json.loads(line) for line in engine.store.events_file.read_text().splitlines()]
            self.assertEqual(events[-1]["event"], "job.completed")


if __name__ == "__main__":
    unittest.main()

