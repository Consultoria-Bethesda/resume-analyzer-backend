import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database, drop_database
from alembic import command
from alembic.config import Config

def setup_db():
    try:
        # Database configuration
        DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/resume_analyzer_test"
        
        print("Starting database setup...")
        
        # Recreate database
        if database_exists(DATABASE_URL):
            print("Dropping existing database...")
            drop_database(DATABASE_URL)
        
        print("Creating new database...")
        create_database(DATABASE_URL)
        
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Reset migrations directory
        versions_dir = os.path.join('alembic', 'versions')
        if os.path.exists(versions_dir):
            print("Cleaning migrations directory...")
            for file in os.listdir(versions_dir):
                if file.endswith('.py'):
                    os.remove(os.path.join(versions_dir, file))
        
        # Create new initial migration
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        
        # Create alembic_version table
        print("Creating alembic version table...")
        with engine.connect() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
            connection.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            connection.commit()
        
        print("Creating initial migration...")
        command.revision(alembic_cfg, 
                        autogenerate=True,
                        message="initial",
                        rev_id="initial_migration")
        
        print("Applying migrations...")
        command.upgrade(alembic_cfg, "head")
        
        print("Database setup completed successfully!")
        
    except Exception as e:
        print(f"Error during database setup: {str(e)}")
        raise

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    setup_db()
