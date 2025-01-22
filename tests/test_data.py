from sqlalchemy.orm import Session
from app.models.user import User

TEST_USER_DATA = {
    "email": "test@example.com",
    "password": "Test@123",
    "name": "Test User"
}

def create_test_user(db: Session):
    user = User(
        email=TEST_USER_DATA["email"],
        name=TEST_USER_DATA["name"]
    )
    user.set_password(TEST_USER_DATA["password"])
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
