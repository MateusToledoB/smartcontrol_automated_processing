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
        "orchestrators.smartsheet_dispatcher_ai",
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
        p2 = run_bot(worker_id)
        processes.append(p2)
        print(f"[{datetime.now()}] Worker {worker_id} apontamento_impar iniciado. PID={p2.pid}")

    try:
        for proc in processes:
            proc.wait()
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        deadline = time.monotonic() + 45
        for proc in processes:
            if proc.poll() is None:
                timeout = max(0.0, deadline - time.monotonic())
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    print(f"[{datetime.now()}] Processo {proc.pid} nao finalizou no prazo. Forcando kill.")
                    proc.kill()

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
            print(f"[{datetime.now()}] Encerramento gracioso do worker apontamento_impar concluido.")
            break

        try:
            run_once()
        except KeyboardInterrupt:
            print(f"[{datetime.now()}] Encerramento gracioso do worker apontamento_impar concluido.")
            break
        except Exception as e:
            print(f"[{datetime.now()}] Erro no ciclo 2.1: {e}")

        if STOP_EVENT.is_set():
            print(f"[{datetime.now()}] Encerramento gracioso do worker apontamento_impar concluido.")
            break

        print(f"[{datetime.now()}] Proximo ciclo 2.1 em {INTERVAL_SECONDS}s")
        sleep_until = time.monotonic() + INTERVAL_SECONDS
        while not STOP_EVENT.is_set():
            restante = sleep_until - time.monotonic()
            if restante <= 0:
                break
            time.sleep(min(1, restante))


if __name__ == "__main__":
    main()
