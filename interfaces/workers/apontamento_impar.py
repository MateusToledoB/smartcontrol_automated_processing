import subprocess
import sys
import time
from datetime import datetime

INTERVAL_SECONDS = 5 * 60
TOTAL_WORKERS = 5

def run_bot(worker_id: int):
    cmd = [
        sys.executable,
        "-m",
        "orchestrators.smartsheet_dispatcher_ai",
        str(worker_id),
    ]
    return subprocess.Popen(cmd)

def run_once():
    processes = []
    for worker_id in range(1, TOTAL_WORKERS + 1):
        p = run_bot(worker_id)
        processes.append(p)
        print(f"[{datetime.now()}] Worker {worker_id} Apontamento impar iniciado. PID={p.pid}")

    for p in processes:
        p.wait()

def main():
    while True:
        start = time.monotonic()
        try:
            run_once()
        except Exception as e:
            print(f"[{datetime.now()}] Erro no ciclo 2.1: {e}")

        print(f"[{datetime.now()}] Próximo ciclo 2.1 em {INTERVAL_SECONDS}s")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
