import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def force_clean_db():
    try:
        # Conecta ao PostgreSQL
        conn = psycopg2.connect(
            dbname="postgres",  # conecta ao banco padrão primeiro
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Força a desconexão de todos os clientes
        cur.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'resume_analyzer_test'
            AND pid <> pg_backend_pid();
        """)
        
        # Drop e recria o banco
        cur.execute("DROP DATABASE IF EXISTS resume_analyzer_test")
        cur.execute("CREATE DATABASE resume_analyzer_test")
        
        print("Banco de dados limpo e recriado com sucesso!")
        
    except Exception as e:
        print(f"Erro: {str(e)}")
        raise
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    force_clean_db()
