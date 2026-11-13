# Run with Native Python

Run `d2-renderer` directly on your host operating system using standard library Python. This option eliminates container runtime overhead and works in environments where Docker or root privileges are unavailable.

## Prerequisites

1. **Python 3.12 or newer**:
   - The service uses strictly the Python standard library. No packages to install via `pip`, and no virtualenv required.
2. **D2 Compiler CLI**:
   - The server delegates diagram compilation to the `d2` executable in your system `$PATH`.
   - Install via Homebrew (macOS / Linux):
     ```bash
     brew install d2
     ```
   - Or install via the official installer script:
     ```bash
     curl -fsSL https://d2lang.com/install.sh | sh -s --
     ```
   - Verify the compiler is available:
     ```bash
     d2 --version
     ```

## Starting the Server

From the root of the repository, run:

```bash
python3 server.py
```

The service begins listening on `http://0.0.0.0:8088`.

Verify reachability:

```bash
curl http://localhost:8088/health
```

The response is `OK`.

## Command-Line Arguments

`server.py` supports standard CLI argument flags:

```text
usage: server.py [-h] [--port PORT] [--bind BIND]

options:
  -h, --help       show this help message and exit
  --port, -p PORT  Port to listen on (default: $PORT or 8088)
  --bind, -b BIND  Address to bind to (default: $HOST or 0.0.0.0)
```

### Examples

Bind strictly to localhost loopback to prevent network access and avoid OS firewall warnings:

```bash
python3 server.py --bind 127.0.0.1 --port 8088
```

Use environment variables (useful in CI runners):

```bash
PORT=9090 HOST=127.0.0.1 python3 server.py
```

## Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PORT` | `8088` | Port number the HTTP service listens on. Overridden by CLI `--port`. |
| `HOST` / `BIND_ADDRESS` | `0.0.0.0` | IP address to bind to. Overridden by CLI `--bind`. |
| `MAX_SOURCE_BYTES` | `262144` (256 KiB) | Maximum allowed size of diagram source text in bytes. |
| `RENDER_TIMEOUT_SECONDS` | `20` | Subprocess compilation timeout in seconds before sending `504 Gateway Timeout`. |
| `CACHE_MAX_AGE_SECONDS` | `86400` (24h) | Value sent in `Cache-Control: public, max-age=...` response header. |

## Running as a Background Daemon

### macOS (`launchd`)
Create a plist file at `~/Library/LaunchAgents/com.user.d2-renderer.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.d2-renderer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string><PATH_TO_REPO>/server.py</string>
        <string>--bind</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8088</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/d2-renderer.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/d2-renderer.err</string>
</dict>
</plist>
```

Load it with `launchctl load ~/Library/LaunchAgents/com.user.d2-renderer.plist`.

### Linux (`systemd` User Service)
Create `~/.config/systemd/user/d2-renderer.service`:

```ini
[Unit]
Description=D2 Diagram Rendering Microservice
After=network.target

[Service]
ExecStart=/usr/bin/python3 <PATH_TO_REPO>/server.py --bind 127.0.0.1 --port 8088
Restart=on-failure
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

Enable and start with:
```bash
systemctl --user enable --now d2-renderer
```

## Security Invariants on Bare Metal

When run on bare metal, `server.py` enforces the same safety constraints as the container:
- **Offline compilation:** Executes `d2 --bundle=false`, ensuring no network requests are made during compilation.
- **Isolated working directory:** Every render executes inside an ephemeral `tempfile.TemporaryDirectory()`, preventing diagram scripts from importing (`...@name`) server files.
- **Strict limits:** Rejects payloads exceeding `MAX_SOURCE_BYTES` (256 KiB) and kills renders exceeding `RENDER_TIMEOUT_SECONDS` (20s).

## Troubleshooting

| Symptom | Cause | Resolution |
| :--- | :--- | :--- |
| `WARNING: 'd2' compiler binary not found in PATH` | D2 CLI is not installed or not exported in `$PATH`. | Install D2 via `brew install d2` or add its location to `$PATH`. |
| Diagram render returns `500 Internal Server Error` | The server attempted to compile a diagram but could not execute `d2`. | Ensure `which d2` succeeds in the shell where `server.py` was started. |
| `OSError: [Errno 48] Address already in use` | Another program uses port 8088. | Pass `--port 9090` to select an alternate port. |
| macOS alerts "Do you want to accept incoming network connections?" | Server bound to `0.0.0.0`. | Run with `--bind 127.0.0.1`. |

## Navigation

- [Setup Guide Index](./README.md)
- [Docker Setup](./010-docker.md)
- [Cloud Run Deployment](./030-cloud-run.md)
