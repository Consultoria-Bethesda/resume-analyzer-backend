from app.routes.auth import router as auth_router
from app.routes.cv_analysis import router as cv_router
from app.routes.user import router as user_router
from app.routes.payment import router as payment_router

__all__ = ['auth_router', 'cv_router', 'user_router', 'payment_router']

