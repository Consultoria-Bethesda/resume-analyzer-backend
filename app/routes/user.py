from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.middleware.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/me")
async def read_user_me(current_user: User = Depends(get_current_user)):
    """Retorna informações do usuário atual"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_active": current_user.is_active
    }

@router.get("/credits")
async def get_user_credits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna os créditos do usuário atual"""
    credits = db.query(User).filter(User.id == current_user.id).first().credits
    return {"credits": credits}

@router.put("/update")
async def update_user(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza informações do usuário"""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        user.name = name
        db.commit()
        return {"message": "User updated successfully"}
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating user")