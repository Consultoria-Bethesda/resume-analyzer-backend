from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db, engine  # Adicionado import do engine
from app.models.user import User
from app.models.user_credits import UserCredits
from app.middleware.auth import get_current_user
from app.config.settings import settings
import stripe
import logging
from sqlalchemy import Table, Column, String, MetaData

logger = logging.getLogger(__name__)
router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

# Criar tabela para rastrear sessões processadas
metadata = MetaData()
processed_sessions = Table(
    'processed_sessions', metadata,
    Column('session_id', String, primary_key=True),
)

# Criar tabela se não existir
metadata.create_all(engine)

@router.post("/create-checkout-session")
async def create_checkout_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info("=== Iniciando criação de sessão de checkout ===")
        logger.info(f"Usuário: {current_user.email}")
        
        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
            logger.error("Configurações do Stripe ausentes")
            raise HTTPException(
                status_code=500,
                detail="Erro de configuração do servidor"
            )
        
        try:
            checkout_data = {
                "payment_method_types": ['card', 'boleto'],
                "line_items": [{
                    'price': settings.STRIPE_PRICE_ID,
                    'quantity': 1,
                }],
                "mode": 'payment',
                "success_url": f'{settings.FRONTEND_URL}/checkout?success=true&session_id={{CHECKOUT_SESSION_ID}}',
                "cancel_url": f'{settings.FRONTEND_URL}/checkout?canceled=true',
                "metadata": {
                    "user_id": str(current_user.id),
                    "email": current_user.email
                },
                "payment_method_options": {
                    "boleto": {
                        "expires_after_days": 3
                    },
                    "card": {
                        "request_three_d_secure": "automatic"
                    }
                },
                "locale": "pt-BR",
                "allow_promotion_codes": True,
                "billing_address_collection": "auto",  # Mudado para 'auto'
                "payment_intent_data": {
                    "description": "4 análises de currículo com IA - Os créditos serão liberados após a confirmação do pagamento (1-3 dias úteis para boleto)"
                }
            }

            # Se o usuário já tem um customer_id, use-o
            if current_user.stripe_customer_id:
                checkout_data["customer"] = current_user.stripe_customer_id
            else:
                # Caso contrário, permita que o Stripe crie um novo customer
                checkout_data["customer_creation"] = "always"
                checkout_data["customer_email"] = current_user.email
            
            logger.info(f"Criando sessão de checkout com dados: {checkout_data}")
            checkout_session = stripe.checkout.Session.create(**checkout_data)
            logger.info(f"Sessão de checkout criada: {checkout_session.id}")
            
            # Se um novo customer foi criado, atualize o user
            if not current_user.stripe_customer_id and checkout_session.customer:
                current_user.stripe_customer_id = checkout_session.customer
                db.commit()
                logger.info(f"Customer ID atualizado: {checkout_session.customer}")
            
            return {"url": checkout_session.url}

        except stripe.error.StripeError as e:
            logger.error(f"Erro do Stripe: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Erro ao processar pagamento: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Erro ao criar sessão de checkout: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao criar sessão de checkout: {str(e)}"
        )

@router.post("/webhook")
async def stripe_webhook(request: Request):
    try:
        # Log do webhook
        body = await request.body()
        logger.info("Webhook recebido do Stripe")
        logger.info(f"Body: {body.decode()}")
        
        # Log do payload recebido
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        logger.info(f"Webhook recebido - Signature: {sig_header}")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Evento Stripe construído: {event.type}")
        except Exception as e:
            logger.error(f"Erro ao construir evento Stripe: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

        if event.type == 'checkout.session.completed':
            session = event.data.object
            logger.info(f"Sessão de checkout completada: {session.id}")
            logger.info(f"Cliente: {session.customer}")
            logger.info(f"Status do pagamento: {session.payment_status}")

            # Buscar usuário
            user = db.query(User).filter(
                User.stripe_customer_id == session.customer
            ).first()

            if not user:
                logger.error(f"Usuário não encontrado para customer_id: {session.customer}")
                return {"status": "error", "message": "Usuário não encontrado"}

            # Adicionar créditos com lock
            user_credits = db.query(UserCredits).filter(
                UserCredits.user_id == user.id
            ).with_for_update().first()

            if user_credits:
                logger.info(f"Créditos antes da atualização: {user_credits.remaining_analyses}")
                user_credits.remaining_analyses += 4
                logger.info(f"Créditos após atualização: {user_credits.remaining_analyses}")
            else:
                logger.info(f"Criando novos créditos para usuário {user.email}")
                user_credits = UserCredits(
                    user_id=user.id,
                    remaining_analyses=4
                )
                db.add(user_credits)

            try:
                db.commit()
                logger.info(f"Créditos salvos com sucesso para {user.email}")
            except Exception as e:
                logger.error(f"Erro ao salvar créditos: {str(e)}")
                db.rollback()
                raise

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
        logger.info(f"Verificando créditos para usuário: {current_user.email}")
        
        user_credits = db.query(UserCredits).filter(
            UserCredits.user_id == current_user.id
        ).first()

        credits = user_credits.remaining_analyses if user_credits else 0
        logger.info(f"Créditos encontrados: {credits} para usuário {current_user.email}")

        return {
            "remaining_analyses": credits,
            "user_id": current_user.id,
            "email": current_user.email
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
        logger.info(f"Verificando pagamento para sessão: {session_id}")
        
        # Verificar se a sessão já foi processada
        result = db.execute(
            processed_sessions.select().where(
                processed_sessions.c.session_id == session_id
            )
        ).first()
        
        if result:
            logger.info(f"Sessão {session_id} já foi processada anteriormente")
            user_credits = db.query(UserCredits).filter(
                UserCredits.user_id == current_user.id
            ).first()
            return {
                "status": "success",
                "message": "Pagamento já foi processado anteriormente",
                "credits": user_credits.remaining_analyses if user_credits else 0
            }
        
        session = stripe.checkout.Session.retrieve(session_id)
        logger.info(f"Status do pagamento: {session.payment_status}")
        
        if session.payment_status == 'paid':
            user_credits = db.query(UserCredits).filter(
                UserCredits.user_id == current_user.id
            ).with_for_update().first()
            
            if not user_credits:
                logger.info(f"Criando novos créditos para usuário {current_user.email}")
                user_credits = UserCredits(
                    user_id=current_user.id,
                    remaining_analyses=4
                )
                db.add(user_credits)
            else:
                logger.info(f"Atualizando créditos existentes para usuário {current_user.email}")
                user_credits.remaining_analyses += 4
            
            try:
                # Marcar sessão como processada
                db.execute(
                    processed_sessions.insert().values(
                        session_id=session_id
                    )
                )
                
                db.commit()
                logger.info(f"Créditos adicionados com sucesso. Novo saldo: {user_credits.remaining_analyses}")
            except Exception as e:
                logger.error(f"Erro ao salvar créditos no banco: {str(e)}")
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro ao processar pagamento: {str(e)}"
                )
            
            return {
                "status": "success",
                "message": "Pagamento confirmado e créditos adicionados",
                "credits": user_credits.remaining_analyses
            }
        
        return {
            "status": "pending",
            "message": "Pagamento ainda não confirmado"
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Erro do Stripe: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao verificar pagamento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify-pending-payments")
async def verify_pending_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Verificando pagamentos pendentes para usuário: {current_user.email}")
        
        # Por enquanto, apenas retorna status ok
        # Você pode expandir esta função posteriormente para verificar pagamentos reais pendentes
        return {
            "status": "success",
            "pending_payments": []
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar pagamentos pendentes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao verificar pagamentos pendentes"
        )

@router.post("/force-add-credits/{session_id}")
async def force_add_credits(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Forçando adição de créditos para sessão: {session_id}")
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
                "message": "Créditos adicionados com sucesso",
                "credits": user_credits.remaining_analyses
            }
        
        return {
            "status": "error",
            "message": "Pagamento não confirmado"
        }
        
    except Exception as e:
        logger.error(f"Erro ao adicionar créditos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
