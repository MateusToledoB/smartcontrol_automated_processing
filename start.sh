#!/bin/sh

echo "Iniciando worker_problema_no_equipamento..."
python interfaces/workers/problema_no_equipamento.py &

echo "Iniciando worker_apontamento_impar..."
python interfaces/workers/apontamento_impar.py &

echo "Iniciando worker_temporarios..."
python interfaces/workers/temporarios.py &

wait