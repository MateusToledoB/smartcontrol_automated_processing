import subprocess
import sys

# Cria um comando em formtado de array, passando o worker_id e exceutando main como um módulo do sistema de pacotes
def run_bot(worker_id):
    comando = [
        sys.executable,
        "orchestrators/smartsheet_dispatcher_temp",
        str(worker_id)
    ]
    return subprocess.Popen(comando)

def main():

    # conjunto dos bots
    processes = []

    print("Iniciando 4 bots em paralelo...\n")

    # Executa os 4 bots
    # cria um novo processo dombot e adiciona este processo a lista 
    for worker_id in range(1, 5):
        p = run_bot(worker_id)
        processes.append(p)
        print(f"Bot {worker_id} iniciado. PID={p.pid}")

    print("\nTodos os bots foram iniciados. Aguardando finalização...")

    # Percorre a lista dos bots aguardando cada processo finalizar para ai sim finalizar o manager, evitando conflitos 
    for p in processes:
        p.wait()

    print("\nTodos os bots finalizaram.")

if __name__ == "__main__":
    main()

       
