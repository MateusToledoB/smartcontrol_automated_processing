import subprocess
import sys
import time
import signal
from datetime import datetime
from threading import Event

INTERVAL_SECONDS = 5 * 60
TOTAL_WORKERS = 1
STOP_EVENT = Event()


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

    def _handle_shutdown(signum, _frame):
        STOP_EVENT.set()
        print(f"[{datetime.now()}] Sinal {signum} recebido no worker pai. Encerrando filhos com graca...")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    for worker_id in range(1, TOTAL_WORKERS + 1):
        if STOP_EVENT.is_set():
            break
        p = run_bot(worker_id)
        processes.append(p)
        print(f"[{datetime.now()}] Worker {worker_id} Problema no equipamento iniciado. PID={p.pid}")

    try:
        for p in processes:
            p.wait()
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        deadline = time.monotonic() + 45
        for p in processes:
            if p.poll() is None:
                timeout = max(0.0, deadline - time.monotonic())
                try:
                    p.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    print(f"[{datetime.now()}] Processo {p.pid} nao finalizou no prazo. Forcando kill.")
                    p.kill()

    if STOP_EVENT.is_set():
        raise KeyboardInterrupt("Encerramento solicitado")


def main():
    def _handle_main_shutdown(signum, _frame):
        STOP_EVENT.set()
        print(f"[{datetime.now()}] Sinal {signum} recebido no worker pai. Encerrando...")

    signal.signal(signal.SIGTERM, _handle_main_shutdown)
    signal.signal(signal.SIGINT, _handle_main_shutdown)

    while True:
        if STOP_EVENT.is_set():
            print(f"[{datetime.now()}] Encerramento gracioso do worker problema_no_equipamento concluido.")
            break

        try:
            run_once()
        except KeyboardInterrupt:
            print(f"[{datetime.now()}] Encerramento gracioso do worker problema_no_equipamento concluido.")
            break
        except Exception as e:
            print(f"[{datetime.now()}] Erro no ciclo 4.1: {e}")

        if STOP_EVENT.is_set():
            print(f"[{datetime.now()}] Encerramento gracioso do worker problema_no_equipamento concluido.")
            break

        print(f"[{datetime.now()}] Proximo ciclo 4.1 em {INTERVAL_SECONDS}s")
        sleep_until = time.monotonic() + INTERVAL_SECONDS
        while not STOP_EVENT.is_set():
            restante = sleep_until - time.monotonic()
            if restante <= 0:
                break
            time.sleep(min(1, restante))


if __name__ == "__main__":
    main()
