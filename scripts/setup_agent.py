#!/usr/bin/env python3
"""Install the Music SFX CLI and register its Codex skill definition."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_FILES = (
    Path("SKILL.md"),
    Path("agents/openai.yaml"),
    Path("references/API.md"),
    Path("references/AUDIO_GUIDE.md"),
)


def default_skill_dir() -> Path:
    codex_root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_root / "skills" / "music-sfx"


def command_result(command: list[str]) -> dict:
    executable = shutil.which(command[0])
    if not executable:
        return {"ok": False, "command": command[0], "error": "not found on PATH"}
    result = subprocess.run(command, capture_output=True, text=True)
    return {
        "ok": result.returncode == 0,
        "command": executable,
        "output": (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else "",
    }


def register_skill(repository: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for relative in SKILL_FILES:
        source = repository / relative
        if not source.is_file():
            raise FileNotFoundError(f"required skill resource is missing: {source}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def verify(destination: Path) -> dict:
    files = {str(relative): (destination / relative).is_file() for relative in SKILL_FILES}
    return {
        "ready": all(files.values()),
        "skill_directory": str(destination),
        "skill_files": files,
        "ffmpeg": command_result(["ffmpeg", "-version"]),
        "ffprobe": command_result(["ffprobe", "-version"]),
        "cli": command_result(["music-sfx", "presets"]),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Install and verify Music SFX for autonomous Codex use")
    result.add_argument("--skill-dir", type=Path, default=default_skill_dir(), help="Codex skill destination")
    result.add_argument("--skip-package", action="store_true", help="register the skill without pip installation")
    result.add_argument("--check", action="store_true", help="verify only; do not install or copy files")
    return result


def main() -> int:
    args = parser().parse_args()
    repository = Path(__file__).resolve().parents[1]
    destination = args.skill_dir.expanduser().resolve()
    if not args.check:
        if not args.skip_package:
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(repository)], check=True)
        register_skill(repository, destination)
    report = verify(destination)
    report["package_install_skipped"] = bool(args.skip_package or args.check)
    report["next_step"] = "Restart Codex so it discovers $music-sfx." if report["ready"] else "Resolve failed checks and run setup again."
    print(json.dumps(report, indent=2, sort_keys=True))
    checks = (report["ready"], report["ffmpeg"]["ok"], report["ffprobe"]["ok"], report["cli"]["ok"])
    return 0 if all(checks) else 2


if __name__ == "__main__":
    raise SystemExit(main())

