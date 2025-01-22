import os
import sys
import shutil
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config
from sqlalchemy_utils import database_exists, create_database, drop_database

def reset_database():
    try:
        # Configurações do banco
        DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/resume_analyzer_test"
        
        print("Iniciando reset do banco de dados...")
        
        # Recria o banco de dados
        if database_exists(DATABASE_URL):
            print("Removendo banco existente...")
            drop_database(DATABASE_URL)
        
        print("Criando novo banco de dados...")
        create_database(DATABASE_URL)
        
        # Remove a pasta alembic e o arquivo alembic.ini se existirem
        alembic_dir = 'alembic'
        alembic_ini = 'alembic.ini'
        if os.path.exists(alembic_dir):
            print("Removendo diretório alembic...")
            shutil.rmtree(alembic_dir)
        if os.path.exists(alembic_ini):
            print("Removendo arquivo alembic.ini...")
            os.remove(alembic_ini)
            
        # Cria o arquivo alembic.ini
        print("Criando novo alembic.ini...")
        with open(alembic_ini, 'w') as f:
            f.write(f"""[alembic]
script_location = alembic
sqlalchemy.url = {DATABASE_URL}

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
        
        # Inicializa novo ambiente alembic
        print("Inicializando novo ambiente alembic...")
        alembic_cfg = Config(alembic_ini)
        command.init(alembic_cfg, 'alembic')
        
        # Cria o env.py customizado
        env_py_content = """
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Importa os modelos
import sys
import os
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
        
        # Sobrescreve o env.py com nossa versão customizada
        with open(os.path.join('alembic', 'env.py'), 'w') as f:
            f.write(env_py_content)
        
        # Gera nova migração
        print("Gerando nova migração...")
        command.revision(alembic_cfg, autogenerate=True, message="initial")
        
        # Aplica a migração
        print("Aplicando migração...")
        command.upgrade(alembic_cfg, "head")
        
        print("Reset do banco de dados concluído com sucesso!")
        
    except Exception as e:
        print(f"Erro durante o reset do banco: {str(e)}")
        raise

if __name__ == "__main__":
    # Adiciona o diretório raiz ao PYTHONPATH
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    reset_database()
