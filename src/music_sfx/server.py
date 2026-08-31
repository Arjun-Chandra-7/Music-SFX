"""Local HTTP API and zero-build web application."""

from __future__ import annotations

import json
import mimetypes
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import __version__
from .engine import AudioEngine, SUPPORTED_INPUTS, require_tools
from .presets import PARAMETERS, presets


def serve(engine: AudioEngine, host: str, port: int) -> None:
    handler = make_handler(engine)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Music SFX Studio running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def make_handler(engine: AudioEngine):
    web_root = files("music_sfx").joinpath("web")
    uploads = engine.data_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        server_version = f"MusicSFX/{__version__}"

        def log_message(self, format: str, *args) -> None:
            print(f"[http] {self.address_string()} {format % args}")

        def json_response(self, value: object, status: int = 200) -> None:
            payload = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def body(self, limit: int = 512 * 1024) -> bytes:
            length = int(self.headers.get("Content-Length", "0"))
            if length > limit:
                raise ValueError(f"request exceeds {limit} bytes")
            return self.rfile.read(length)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/health":
                try:
                    require_tools()
                    tools_ready = True
                except RuntimeError:
                    tools_ready = False
                self.json_response({"status": "ok", "version": __version__, "ffmpeg": tools_ready})
            elif path == "/api/presets":
                self.json_response({"presets": presets(), "parameters": PARAMETERS})
            elif path == "/api/jobs":
                self.json_response({"jobs": engine.store.list()})
            elif path.startswith("/api/jobs/"):
                job = engine.store.get(path.rsplit("/", 1)[-1])
                self.json_response(job or {"error": "not found"}, 200 if job else 404)
            elif path.startswith("/media/"):
                self.serve_media(path.removeprefix("/media/"))
            else:
                self.serve_static(path)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                if path == "/api/upload":
                    self.upload()
                elif path == "/api/render":
                    request = json.loads(self.body().decode())
                    if request.get("output") and not Path(request["output"]).is_absolute():
                        # Browser clients name a deliverable; the server owns its storage root.
                        request["output"] = str(engine.data_dir / "renders" / Path(request["output"]).name)
                    job = engine.prepare(request)
                    threading.Thread(target=engine.execute, args=(job,), daemon=True).start()
                    self.json_response(job, HTTPStatus.ACCEPTED)
                else:
                    self.json_response({"error": "not found"}, 404)
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                self.json_response({"error": str(exc)}, 400)
            except Exception as exc:
                self.json_response({"error": str(exc)}, 500)

        def upload(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 500 * 1024 * 1024:
                raise ValueError("audio file must be between 1 byte and 500 MB")
            original = Path(unquote(self.headers.get("X-Filename", "audio.wav"))).name
            suffix = Path(original).suffix.lower()
            if suffix not in SUPPORTED_INPUTS:
                raise ValueError(f"unsupported audio type: {suffix}")
            target = uploads / f"{uuid.uuid4().hex[:10]}-{original}"
            remaining = length
            with target.open("xb") as stream:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("incomplete upload")
                    stream.write(chunk)
                    remaining -= len(chunk)
            self.json_response({"path": str(target), "name": original, "media_url": f"/media/uploads/{target.name}"}, 201)

        def serve_media(self, relative: str) -> None:
            candidate = (engine.data_dir / unquote(relative)).resolve()
            if engine.data_dir not in candidate.parents or not candidate.is_file():
                self.send_error(404)
                return
            self.serve_file(candidate)

        def serve_static(self, path: str) -> None:
            name = "index.html" if path in {"", "/"} else path.lstrip("/")
            if "/" in name or name.startswith("."):
                self.send_error(404)
                return
            resource = web_root.joinpath(name)
            if not resource.is_file():
                self.send_error(404)
                return
            data = resource.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def serve_file(self, path: Path) -> None:
            size = path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    self.wfile.write(chunk)

    return Handler
