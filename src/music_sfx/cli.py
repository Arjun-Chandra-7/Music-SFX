"""Command-line interface used by people and autonomous agents."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .engine import AudioEngine, probe
from .presets import PARAMETERS, presets


def data_dir() -> Path:
    return Path(os.environ.get("MUSIC_SFX_DATA_DIR", ".music-sfx")).resolve()


def output(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="music-sfx", description="Agent-ready professional audio processing")
    root.add_argument("--data-dir", type=Path, default=data_dir(), help="job history and render storage")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("presets", help="list available presets")
    inspect = commands.add_parser("inspect", help="read technical audio metadata")
    inspect.add_argument("input", type=Path)
    process = commands.add_parser("process", help="render one audio asset")
    process.add_argument("input", type=Path)
    process.add_argument("--output", type=Path)
    process.add_argument("--preset", default="clean_master", choices=presets().keys())
    process.add_argument("--rights", default="unknown", choices=["owned", "licensed", "public_domain", "unknown"])
    process.add_argument("--actor", default="cli")
    process.add_argument("--intent", default="audio enhancement")
    process.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    process.add_argument("--overwrite", action="store_true")
    process.add_argument("--dry-run", action="store_true")
    serve = commands.add_parser("serve", help="run browser UI and local API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    jobs = commands.add_parser("jobs", help="list recent job manifests")
    jobs.add_argument("--limit", type=int, default=20)
    return root


def parse_values(entries: list[str]) -> dict:
    values = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(f"Expected KEY=VALUE, got {entry!r}")
        key, raw = entry.split("=", 1)
        if key not in PARAMETERS:
            raise ValueError(f"Unknown parameter {key!r}; choose from {', '.join(PARAMETERS)}")
        values[key] = float(raw)
    return values


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    engine = AudioEngine(args.data_dir)
    try:
        if args.command == "presets":
            output({"presets": presets(), "parameters": PARAMETERS})
        elif args.command == "inspect":
            output({"path": str(args.input.resolve()), "metadata": probe(args.input.resolve())})
        elif args.command == "jobs":
            output({"jobs": engine.store.list(args.limit)})
        elif args.command == "process":
            request = {
                "input": str(args.input), "output": str(args.output) if args.output else None,
                "preset": args.preset, "parameters": parse_values(args.set), "rights": args.rights,
                "actor": args.actor, "intent": args.intent, "overwrite": args.overwrite, "dry_run": args.dry_run,
            }
            job = engine.process(request)
            output(job)
            return 0 if job["status"] in {"completed", "dry_run"} else 2
        elif args.command == "serve":
            from .server import serve
            serve(engine, args.host, args.port)
    except (ValueError, RuntimeError, OSError) as exc:
        output({"error": str(exc)})
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

