#!/bin/sh

echo "Iniciando worker_problema..."
python interfaces/workers/problema_no_equipamento.py &

echo "Iniciando worker_temporarios..."
python interfaces/workers/temporarios.py &

wait