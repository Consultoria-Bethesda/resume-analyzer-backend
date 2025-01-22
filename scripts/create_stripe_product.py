import os
import sys
# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stripe
from app.config.settings import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_product_and_price():
    try:
        # Criar produto
        product = stripe.Product.create(
            name="Pacote de Análises",
            description="4 análises de currículo com IA"
        )
        
        # Criar preço
        price = stripe.Price.create(
            product=product.id,
            unit_amount=2997,  # R$ 29,97 em centavos
            currency="brl",
            recurring=None  # Pagamento único
        )
        
        print(f"Produto criado com ID: {product.id}")
        print(f"Preço criado com ID: {price.id}")
        print("\nAdicione o PRICE_ID ao seu arquivo .env:")
        print(f"STRIPE_PRICE_ID={price.id}")
        
        return price.id
    except Exception as e:
        print(f"Erro ao criar produto/preço: {str(e)}")
        return None

if __name__ == "__main__":
    create_stripe_product_and_price()
