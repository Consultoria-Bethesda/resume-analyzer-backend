import os
import sys
import shutil
import time
from alembic import command
from alembic.config import Config

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings

def reset_migrations():
    try:
        print("Removendo diretórios existentes...")
        # Remove diretórios existentes
        if os.path.exists('alembic'):
            shutil.rmtree('alembic', ignore_errors=True)
            time.sleep(1)
        
        if os.path.exists('alembic.ini'):
            os.remove('alembic.ini')
            time.sleep(1)
            
        print("Criando nova estrutura...")
        # Cria a estrutura de pastas necessária
        os.makedirs('alembic', exist_ok=True)
        os.makedirs('alembic/versions', exist_ok=True)
            
        # Cria/atualiza o arquivo alembic.ini com a URL já formatada
        database_url = f"postgresql://{settings.PGUSER}:{settings.PGPASSWORD}@{settings.PGHOST}:{settings.PGPORT}/{settings.PGDATABASE}"
        
        alembic_ini = "alembic.ini"
        with open(alembic_ini, 'w') as f:
            f.write(f"""[alembic]
script_location = alembic
sqlalchemy.url = {database_url}

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""")
        
        print("Configurando Alembic...")
        # Configura o Alembic
        alembic_cfg = Config("alembic.ini")
        
        # Remove novamente o diretório alembic para garantir que está vazio
        if os.path.exists('alembic'):
            shutil.rmtree('alembic', ignore_errors=True)
            time.sleep(1)
        
        print("Inicializando ambiente Alembic...")
        # Inicializa o ambiente Alembic
        command.init(alembic_cfg, 'alembic')
        
        print("Configurando env.py...")
        # Substitui o conteúdo do env.py
        env_py_content = """
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.models import *

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""
        
        with open(os.path.join('alembic', 'env.py'), 'w') as f:
            f.write(env_py_content)
        
        print("Criando migração inicial...")
        # Cria nova migração inicial
        command.revision(alembic_cfg, 
                        autogenerate=True,
                        message="initial")
        
        print("Aplicando migração...")
        # Aplica a migração
        command.upgrade(alembic_cfg, "head")
        
        print("Estrutura de migrações criada com sucesso!")
        
    except Exception as e:
        print(f"Erro ao resetar migrações: {str(e)}")
        raise

if __name__ == "__main__":
    reset_migrations()
