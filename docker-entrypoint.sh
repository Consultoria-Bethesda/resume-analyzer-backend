#!/bin/bash

# Adiciona o diretório atual ao PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/app"

# Esperar pelo banco de dados
echo "Aguardando banco de dados..."
sleep 5

# Reset e inicialização das migrações
echo "Resetando e inicializando migrações..."
python scripts/reset_and_init_migrations.py

# Executar migrações
echo "Executando migrações..."
alembic upgrade head

# Inicializar banco de dados
echo "Inicializando banco de dados..."
python scripts/init_db.py

# Iniciar a aplicação
echo "Iniciando aplicação..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
