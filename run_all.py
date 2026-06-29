"""Single entrypoint — runs webapp server + both bots as subprocesses."""
import subprocess, sys, os, signal, logging, time

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))

NAMES = ["Webapp", "Crypto", "NEPSE"]
CMDS  = [
    [sys.executable, os.path.join(BASE, "serve_webapp.py")],
    [sys.executable, os.path.join(BASE, "main.py")],
    [sys.executable, os.path.join(BASE, "nepse", "main.py")],
]
CWDS  = [BASE, BASE, os.path.join(BASE, "nepse")]

procs = []

def shutdown(sig, frame):
    log.info("Shutting down...")
    for p in procs:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

for name, cmd, cwd in zip(NAMES, CMDS, CWDS):
    log.info(f"Starting {name}...")
    procs.append(subprocess.Popen(cmd, cwd=cwd))

log.info("All 3 processes running.")

while True:
    for i, p in enumerate(procs):
        ret = p.poll()
        if ret is not None:
            log.warning(f"{NAMES[i]} crashed (exit {ret}), restarting...")
            procs[i] = subprocess.Popen(CMDS[i], cwd=CWDS[i])
    time.sleep(10)
