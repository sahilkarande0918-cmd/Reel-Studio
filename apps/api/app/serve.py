"""Run the local processing stack: public HTTPS tunnel + API (+ worker).

    python -m app.serve --tunnel devtunnel  # Microsoft Dev Tunnels (stable URL, 443 only; works behind Fortinet)
    python -m app.serve                     # Cloudflare quick tunnel (needs outbound 7844)
    python -m app.serve --tunnel tailscale  # Tailscale Funnel (needs controlplane + DERP reachable)
    python -m app.serve --tunnel none

A quick tunnel is free and needs no account, but its URL changes on every start. The API heartbeats
the new URL to Supabase (`backend_endpoints`), so the deployed frontend finds it without a redeploy.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
CANDIDATES = [
    shutil.which("cloudflared"),
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
]


def find_cloudflared() -> str:
    for c in CANDIDATES:
        if c and Path(c).exists():
            return c
    sys.exit("cloudflared not found. Install it: winget install Cloudflare.cloudflared")


def start_tunnel(port: int) -> tuple[subprocess.Popen, str]:
    proc = subprocess.Popen(
        [
            find_cloudflared(),
            "tunnel",
            "--no-autoupdate",
            "--protocol",
            "http2",
            "--url",
            f"http://127.0.0.1:{port}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.stdout
    for line in proc.stdout:
        if m := URL_RE.search(line):
            # keep draining output so the pipe never blocks the tunnel
            threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()
            return proc, m.group(0)
    sys.exit("cloudflared exited before printing a tunnel URL")


def start_funnel(port: int) -> tuple[subprocess.Popen, str]:
    """Tailscale Funnel: free, works where only outbound 443 is allowed, stable *.ts.net URL."""
    ts = shutil.which("tailscale") or r"C:\Program Files\Tailscale\tailscale.exe"
    if not Path(ts).exists():
        sys.exit("tailscale not found. Install from https://tailscale.com/download and run `tailscale up`.")
    status = json.loads(
        subprocess.run([ts, "status", "--json"], capture_output=True, text=True, check=True).stdout
    )
    url = "https://" + status["Self"]["DNSName"].rstrip(".")
    return subprocess.Popen([ts, "funnel", str(port)]), url


DEVTUNNEL_URL_RE = re.compile(r"https://[a-z0-9-]+\.[a-z0-9]+\.devtunnels\.ms")
DEVTUNNEL_ID = "reel-studio"


def find_devtunnel() -> str:
    found = shutil.which("devtunnel") or next(
        Path(os.environ.get("LOCALAPPDATA", "")).glob(
            "Microsoft/WinGet/Packages/Microsoft.devtunnel_*/devtunnel.exe"
        ),
        None,
    )
    if not found:
        sys.exit(
            "devtunnel not found. Install it: winget install Microsoft.devtunnel, then `devtunnel user login -g -d`"
        )
    return str(found)


def start_devtunnel(port: int) -> tuple[subprocess.Popen, str]:
    """Persistent named dev tunnel: same URL every start. Anonymous relay access is required so the
    browser can call it; every API route still demands a Supabase JWT (the real gate)."""
    dt = find_devtunnel()
    run = lambda *a: subprocess.run([dt, *a], capture_output=True, text=True)  # noqa: E731
    if run("show", DEVTUNNEL_ID).returncode != 0:
        r = run("create", DEVTUNNEL_ID, "--allow-anonymous")
        if r.returncode != 0:
            sys.exit(
                f"devtunnel create failed (logged in? `devtunnel user login -g -d`):\n{r.stdout}{r.stderr}"
            )
    run("port", "create", DEVTUNNEL_ID, "-p", str(port), "--protocol", "http")  # no-op if it exists
    # the URL is fixed per tunnel+port; read it from `show` (host output is buffered when piped)
    urls = [u for u in DEVTUNNEL_URL_RE.findall(run("show", DEVTUNNEL_ID).stdout) if f"-{port}." in u]
    if not urls:
        sys.exit(f"devtunnel has no URL for port {port}")
    return subprocess.Popen(
        [dt, "host", DEVTUNNEL_ID], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    ), urls[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument(
        "--tunnel", choices=["cloudflare", "devtunnel", "tailscale", "none"], default="cloudflare"
    )
    ap.add_argument("--no-worker", action="store_true")
    args = ap.parse_args()

    # name -> (start function, running process); the watchdog restarts any child that exits.
    children: dict[str, list] = {}
    if args.tunnel != "none":
        starter = {"cloudflare": start_tunnel, "devtunnel": start_devtunnel, "tailscale": start_funnel}
        tunnel, url = starter[args.tunnel](args.port)
        children["tunnel"] = [lambda: starter[args.tunnel](args.port)[0], tunnel]
        os.environ["PUBLIC_API_URL"] = url
        print(f"Tunnel: {url}", flush=True)
    from app.core import engine_state

    if not args.no_worker and Path(__file__).with_name("workers").joinpath("run.py").exists():
        worker = lambda: subprocess.Popen(  # noqa: E731
            [sys.executable, "-m", "app.workers.run"], cwd=Path(__file__).parents[1]
        )
        children["worker"] = [worker, None if engine_state.paused() else worker()]

    stop = threading.Event()

    def watchdog() -> None:
        """A crashed tunnel or worker made the site show 'Engine offline' until a manual restart. The dashboard's
        engine switch pauses processing: the worker (GPU, renders, AI) is stopped and stays stopped while the
        API and tunnel keep answering, so the same switch can turn processing back on."""
        while not stop.wait(3):
            if "worker" in children:
                entry = children["worker"]
                running = entry[1] is not None and entry[1].poll() is None
                if engine_state.paused():
                    if running:
                        print("[serve] processing paused from the dashboard: stopping the worker", flush=True)
                        if sys.platform == "win32":  # the whole tree: ffmpeg/Chrome children of a running job
                            subprocess.run(["taskkill", "/PID", str(entry[1].pid), "/T", "/F"], capture_output=True)
                        entry[1].kill()
                        engine_state.free_gpu()
                    entry[1] = None
                    continue
                if entry[1] is None:
                    print("[serve] processing resumed: starting the worker", flush=True)
                    entry[1] = entry[0]()
                    continue
            for name, entry in children.items():
                if entry[1] is not None and entry[1].poll() is not None:
                    print(f"[serve] {name} exited ({entry[1].returncode}); restarting", flush=True)
                    try:
                        entry[1] = entry[0]()
                    except (OSError, SystemExit) as e:  # e.g. network down: try again next round
                        print(f"[serve] {name} restart failed: {e}", flush=True)

    threading.Thread(target=watchdog, daemon=True).start()
    if args.tunnel != "none" and sys.platform == "win32":
        # The public engine must answer while the laptop is idle: ask Windows not to idle-sleep while this process runs
        # (ES_CONTINUOUS | ES_SYSTEM_REQUIRED, held by the main thread that runs uvicorn; released when it exits).
        # A closed lid or a manual Sleep still sleeps.
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)

    import uvicorn

    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, app_dir=str(Path(__file__).parents[1]))
    finally:
        stop.set()
        for entry in children.values():
            if entry[1] is not None:
                entry[1].terminate()


if __name__ == "__main__":
    main()
