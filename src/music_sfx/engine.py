"""FFmpeg-backed deterministic audio render engine."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .policy import evaluate
from .presets import PARAMETERS, preset
from .store import JobStore

SUPPORTED_INPUTS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".aiff", ".aif"}
SUPPORTED_OUTPUTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_tools() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise RuntimeError(f"Missing required system tools: {', '.join(missing)}")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    require_tools()
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size,bit_rate,format_name:stream=codec_name,codec_type,sample_rate,channels", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
    fmt = data.get("format", {})
    return {
        "duration": round(float(fmt.get("duration", 0)), 3),
        "size": int(fmt.get("size", 0)),
        "bit_rate": int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else None,
        "format": fmt.get("format_name"),
        "codec": audio.get("codec_name"),
        "sample_rate": int(audio.get("sample_rate", 0)) if audio.get("sample_rate") else None,
        "channels": audio.get("channels"),
    }


def validate_values(values: dict) -> dict:
    normalized = {}
    for key, spec in PARAMETERS.items():
        value = float(values.get(key, 0 if key != "width" and key != "wet" else 100))
        if not spec["min"] <= value <= spec["max"]:
            raise ValueError(f"{key} must be between {spec['min']} and {spec['max']}")
        normalized[key] = value
    return normalized


def build_filters(values: dict, special: str | None = None) -> str:
    filters: list[str] = ["aformat=channel_layouts=stereo", "highpass=f=32"]
    if special == "radio":
        filters += ["highpass=f=280", "lowpass=f=4800"]
    if values["low_gain"]:
        filters.append(f"bass=g={values['low_gain']}:f=120:w=0.7")
    if values["presence"]:
        filters.append(f"equalizer=f=3200:t=q:w=0.8:g={values['presence']}")
    if values["air"]:
        filters.append(f"treble=g={values['air']}:f=9000:w=0.6")
    compression = values["compression"]
    if compression > 0:
        threshold = -10 - compression * 0.18
        ratio = 1.2 + compression * 0.058
        filters.append(f"acompressor=threshold={threshold:.2f}dB:ratio={ratio:.2f}:attack=12:release=180:makeup=1.5")
    width = values["width"] / 100
    if abs(width - 1) > 0.001:
        # Stereo mid/side width matrix. Mono sources are normalized upstream.
        side = width
        filters.append(f"pan=stereo|c0={(1+side)/2:.4f}*c0+{(1-side)/2:.4f}*c1|c1={(1-side)/2:.4f}*c0+{(1+side)/2:.4f}*c1")
    space = values["space"]
    if space > 0:
        delay = int(35 + space * 2.2)
        decay = min(0.82, 0.14 + space / 130)
        filters.append(f"aecho=0.8:0.75:{delay}|{delay * 2}:{decay:.3f}|{decay * 0.55:.3f}")
    wet = values["wet"] / 100
    if wet < 1:
        filters.append(f"volume={wet:.3f}")
    if values["output_gain"]:
        filters.append(f"volume={values['output_gain']}dB")
    # Conservative true-peak approximation and fixed output sample layout.
    filters += ["alimiter=limit=0.891:attack=5:release=50", "aresample=48000"]
    return ",".join(filters)


def codec_args(output: Path) -> list[str]:
    suffix = output.suffix.lower()
    if suffix == ".wav":
        return ["-c:a", "pcm_s24le"]
    if suffix == ".flac":
        return ["-c:a", "flac"]
    if suffix == ".mp3":
        return ["-c:a", "libmp3lame", "-b:a", "320k"]
    if suffix == ".m4a":
        return ["-c:a", "aac", "-b:a", "256k"]
    if suffix == ".opus":
        return ["-c:a", "libopus", "-b:a", "192k"]
    if suffix == ".ogg":
        return ["-c:a", "libvorbis", "-q:a", "8"]
    raise ValueError(f"Unsupported output format: {suffix}")


class AudioEngine:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store = JobStore(self.data_dir)

    def prepare(self, request: dict) -> dict:
        input_path = Path(request["input"]).expanduser().resolve()
        if input_path.suffix.lower() not in SUPPORTED_INPUTS:
            raise ValueError(f"Unsupported input format: {input_path.suffix}")
        selected = request.get("preset", "clean_master")
        preset_data = preset(selected)
        values = validate_values({**preset_data["values"], **request.get("parameters", {})})
        output_path = Path(request.get("output") or (self.data_dir / "renders" / f"{input_path.stem}-{selected}.wav")).expanduser().resolve()
        if output_path.suffix.lower() not in SUPPORTED_OUTPUTS:
            raise ValueError(f"Unsupported output format: {output_path.suffix}")
        decision = evaluate(input_path=input_path, output_path=output_path, rights=request.get("rights", "unknown"), overwrite=bool(request.get("overwrite")))
        job_id = uuid.uuid4().hex[:12]
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if request.get("overwrite") else "-n", "-i", str(input_path), "-vn", "-af", build_filters(values, preset_data.get("special")), *codec_args(output_path), str(output_path)]
        job = {
            "id": job_id, "status": "prepared", "created_at": utc_now(), "updated_at": utc_now(),
            "input": str(input_path), "output": str(output_path), "preset": selected, "parameters": values,
            "rights": request.get("rights", "unknown"), "policy": decision.as_dict(),
            "intent": request.get("intent", "audio enhancement"), "actor": request.get("actor", "unknown"),
            "command": command, "dry_run": bool(request.get("dry_run")),
        }
        self.store.write(job)
        self.store.event(job_id, "job.prepared", {"policy": decision.as_dict()})
        return job

    def execute(self, job: dict) -> dict:
        if not job["policy"]["allowed"]:
            job.update(status="blocked", updated_at=utc_now())
            self.store.write(job)
            self.store.event(job["id"], "job.blocked", {"reasons": job["policy"]["reasons"]})
            return job
        if job["dry_run"]:
            job.update(status="dry_run", updated_at=utc_now())
            self.store.write(job)
            self.store.event(job["id"], "job.dry_run")
            return job
        require_tools()
        output = Path(job["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        job.update(status="processing", updated_at=utc_now())
        self.store.write(job)
        self.store.event(job["id"], "job.started")
        try:
            source_meta = probe(Path(job["input"]))
            result = subprocess.run(job["command"], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr.strip()[-2000:] or "ffmpeg failed")
            job.update(
                status="completed", updated_at=utc_now(),
                source={"sha256": file_hash(Path(job["input"])), "metadata": source_meta},
                result={"sha256": file_hash(output), "metadata": probe(output)},
            )
            self.store.event(job["id"], "job.completed", {"output": str(output), "sha256": job["result"]["sha256"]})
        except Exception as exc:
            job.update(status="failed", updated_at=utc_now(), error=str(exc))
            self.store.event(job["id"], "job.failed", {"error": str(exc)})
        self.store.write(job)
        return job

    def process(self, request: dict) -> dict:
        return self.execute(self.prepare(request))
