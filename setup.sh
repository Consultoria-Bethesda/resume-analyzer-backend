#!/bin/bash

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # No Windows: .\venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Executar migrações do banco de dados
alembic upgrade head

# Inicializar banco de dados com todas as tabelas
python scripts/init_db.py

echo "Setup completo!"
