from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class UserCredits(Base):
    __tablename__ = "user_credits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    remaining_analyses = Column(Integer, default=0)