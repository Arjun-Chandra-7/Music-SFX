# Local API

Start the service with:

```bash
music-sfx serve --host 127.0.0.1 --port 8765
```

The API has no authentication and is intentionally loopback-only by default. Do not expose it to a public network without adding an authenticated reverse proxy and an explicit storage policy.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Engine and FFmpeg readiness |
| `GET` | `/api/presets` | Presets, parameter ranges, and labels |
| `GET` | `/api/jobs` | Recent job manifests |
| `GET` | `/api/jobs/{id}` | One job manifest/status |
| `POST` | `/api/upload` | Raw audio upload, maximum 500 MB |
| `POST` | `/api/render` | Queue a render; returns HTTP 202 |
| `GET` | `/media/{relative-path}` | Read an output stored under the data directory |

### Upload

Send the audio bytes as `application/octet-stream` with an encoded `X-Filename` header. The response contains the absolute server-side `path`; pass that path to `/api/render`.

### Render request

```json
{
  "input": "/absolute/path/source.wav",
  "output": "/absolute/path/master.wav",
  "preset": "clean_master",
  "parameters": {"presence": 1.5, "compression": 35},
  "rights": "licensed",
  "actor": "channel-agent-7",
  "intent": "Episode 12 final master",
  "overwrite": false,
  "dry_run": false
}
```

Poll `/api/jobs/{id}` until `status` is `completed`, `failed`, `blocked`, or `dry_run`. Never treat the initial `prepared` response as a completed render.

Job history is stored under `.music-sfx/jobs/`; the append-only event stream is `.music-sfx/events.jsonl`. Set `MUSIC_SFX_DATA_DIR` or pass `--data-dir` to relocate both.

