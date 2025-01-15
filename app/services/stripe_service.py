import stripe
from app.config.settings import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_checkout_session(customer_email: str):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': 'Pacote de Análises',
                        'description': '4 análises de currículo com IA'
                    },
                    'unit_amount': 2997,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{settings.FRONTEND_URL}/payment/success',
            cancel_url=f'{settings.FRONTEND_URL}/payment/cancel',
            customer_email=customer_email
        )
        return session
    except Exception as e:
        raise Exception(f"Erro ao criar sessão de checkout: {str(e)}")