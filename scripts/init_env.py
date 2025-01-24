from dotenv import load_dotenv
import os

def init_env():
    load_dotenv()
    
    # Verificar se as variáveis foram carregadas
    required_vars = [
        'SECRET_KEY',
        'OPENAI_API_KEY',
        'STRIPE_SECRET_KEY',
        'STRIPE_PUBLIC_KEY',
        'STRIPE_WEBHOOK_SECRET',
        'STRIPE_PRICE_ID'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        print(f"{var}: {'✓' if value else '✗'}")

if __name__ == "__main__":
    init_env()