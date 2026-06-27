"""Single entrypoint — runs both bots as subprocesses."""
import subprocess, sys, os, signal, logging

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))

procs = []

def shutdown(sig, frame):
    log.info("Shutting down both bots...")
    for p in procs:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

log.info("Starting Crypto Signal Bot...")
p1 = subprocess.Popen([sys.executable, os.path.join(BASE, "main.py")], cwd=BASE)
procs.append(p1)

log.info("Starting NEPSE Signal Bot...")
p2 = subprocess.Popen([sys.executable, os.path.join(BASE, "nepse", "main.py")], cwd=os.path.join(BASE, "nepse"))
procs.append(p2)

log.info("Both bots running. Waiting...")
# Wait and restart any crashed bot
while True:
    for i, p in enumerate(procs):
        ret = p.poll()
        if ret is not None:
            name = "Crypto" if i == 0 else "NEPSE"
            log.warning(f"{name} bot crashed (exit {ret}), restarting...")
            if i == 0:
                procs[0] = subprocess.Popen([sys.executable, os.path.join(BASE, "main.py")], cwd=BASE)
            else:
                procs[1] = subprocess.Popen([sys.executable, os.path.join(BASE, "nepse", "main.py")], cwd=os.path.join(BASE, "nepse"))
    import time; time.sleep(10)
