from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.user_credits import UserCredits
from app.middleware.auth import get_current_user
from app.config.settings import settings
import stripe
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/create-checkout-session")
async def create_checkout_session(current_user: User = Depends(get_current_user)):
    try:
        logger.info(f"Criando sessão de checkout para: {current_user.email}")
        
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
            success_url=f'{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{settings.FRONTEND_URL}/payment/cancel',
            customer_email=current_user.email
        )
        
        logger.info(f"Sessão criada: {session.id}")
        return {"checkout_url": session.url}
        
    except Exception as e:
        logger.error(f"Erro ao criar sessão: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        logger.info("Webhook do Stripe recebido")
        
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            logger.error(f"Erro ao validar webhook: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            customer_email = session.get('customer_email')
            
            user = db.query(User).filter(User.email == customer_email).first()
            if not user:
                logger.error(f"Usuário não encontrado: {customer_email}")
                return {"status": "error", "message": "Usuário não encontrado"}

            user_credits = db.query(UserCredits).filter(
                UserCredits.user_id == user.id
            ).first()

            if user_credits:
                user_credits.remaining_analyses += 4
            else:
                user_credits = UserCredits(
                    user_id=user.id,
                    remaining_analyses=4
                )
                db.add(user_credits)

            db.commit()

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/verify-credits")
async def verify_credits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user_credits = db.query(UserCredits).filter(
            UserCredits.user_id == current_user.id
        ).first()

        return {
            "remaining_analyses": user_credits.remaining_analyses if user_credits else 0
        }
    except Exception as e:
        logger.error(f"Erro ao verificar créditos: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao verificar créditos"
        )

@router.get("/verify-payment/{session_id}")
async def verify_payment(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            user_credits = db.query(UserCredits).filter(
                UserCredits.user_id == current_user.id
            ).first()
            
            if not user_credits:
                user_credits = UserCredits(
                    user_id=current_user.id,
                    remaining_analyses=4
                )
                db.add(user_credits)
            else:
                user_credits.remaining_analyses += 4
            
            db.commit()
            
            return {
                "status": "success",
                "message": "Pagamento confirmado e créditos adicionados",
                "credits": user_credits.remaining_analyses
            }
        
        return {
            "status": "pending",
            "message": "Pagamento ainda não confirmado"
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar pagamento: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))