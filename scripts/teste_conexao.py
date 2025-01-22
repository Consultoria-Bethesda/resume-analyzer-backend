import psycopg2

def testar_conexao():
    try:
        # Tenta conectar ao PostgreSQL
        conn = psycopg2.connect(
            dbname="resume_analyzer_test",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        print("Conexão ao banco resume_analyzer_test bem sucedida!")
        
        # Verifica as tabelas existentes
        cur = conn.cursor()
        
        # Lista todas as tabelas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        tabelas = cur.fetchall()
        
        if tabelas:
            print("\nTabelas encontradas:")
            for tabela in tabelas:
                print(f"- {tabela[0]}")
                
                # Para cada tabela, mostra suas colunas
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s
                """, (tabela[0],))
                
                colunas = cur.fetchall()
                for coluna in colunas:
                    print(f"  - {coluna[0]} ({coluna[1]})")
        else:
            print("\nNenhuma tabela encontrada no banco de dados.")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {str(e)}")

if __name__ == "__main__":
    testar_conexao()
