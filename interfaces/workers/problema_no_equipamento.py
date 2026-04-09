import subprocess
import sys
import time
from datetime import datetime

INTERVAL_SECONDS = 10 * 60
TOTAL_WORKERS = 1

def run_bot(worker_id: int):
    cmd = [
        sys.executable,
        "-m",
        "orchestrators.smartsheet_dispatcher_pe",
        str(worker_id),
    ]
    return subprocess.Popen(cmd)

def run_once():
    processes = []
    for worker_id in range(1, TOTAL_WORKERS + 1):
        p = run_bot(worker_id)
        processes.append(p)
        print(f"[{datetime.now()}] Worker {worker_id} iniciado. PID={p.pid}")

    for p in processes:
        p.wait()

def main():
    while True:
        start = time.monotonic()
        try:
            run_once()
        except Exception as e:
            print(f"[{datetime.now()}] Erro no ciclo: {e}")

        elapsed = time.monotonic() - start
        sleep_for = max(0, INTERVAL_SECONDS - elapsed)
        print(f"[{datetime.now()}] Próximo ciclo em {sleep_for:.0f}s")
        time.sleep(sleep_for)

if __name__ == "__main__":
    main()
