import subprocess
import sys

def run_bot(worker_id):
    comando = [
        sys.executable,
        "-m",
        "orchestrators.smartsheet_dispatcher_temp",
        str(worker_id)
    ]
    return subprocess.Popen(comando)

def main():
    print("Iniciando 1 worker...\n")

    p = run_bot(1)
    print(f"Bot 1 iniciado. PID={p.pid}")

    p.wait()

    print("\nWorker finalizado.")

if __name__ == "__main__":
    main()