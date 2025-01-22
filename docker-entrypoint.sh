#!/bin/bash

# Esperar pelo banco de dados (opcional, mas recomendado)
echo "Aguardando banco de dados..."
sleep 5

# Executar migrações
echo "Executando migrações..."
alembic upgrade head

# Inicializar banco de dados
echo "Inicializando banco de dados..."
python scripts/init_db.py

# Iniciar a aplicação
echo "Iniciando aplicação..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
