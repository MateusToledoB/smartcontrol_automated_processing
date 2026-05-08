#!/bin/sh

echo "Iniciando worker_problema..."
python interfaces/workers/problema_no_equipamento.py &

echo "Iniciando worker_apontamento_impar..."
python interfaces/workers/apontamento_impar.py &

wait