from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from database import get_db
import models, auth_utils

router = APIRouter()

class RegisterRequest(BaseModel):
    email:     EmailStr
    full_name: str
    password:  str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      str
    full_name:    str
    role:         str

class UserResponse(BaseModel):
    id:         str
    email:      str
    full_name:  str
    role:       str
    is_active:  bool
    is_verified: bool

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        email           = data.email,
        full_name       = data.full_name,
        hashed_password = auth_utils.hash_password(data.password),
    )
    db.add(user)
    db.flush()

    # Auto-create a vault for the new user
    vault = models.Vault(user_id=user.id)
    db.add(vault)
    db.commit()
    db.refresh(user)

    token = auth_utils.create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        full_name=user.full_name,
        role=user.role.value
    )

@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not auth_utils.verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = auth_utils.create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        full_name=user.full_name,
        role=user.role.value
    )

@router.get("/me", response_model=UserResponse)
def me(current_user: models.User = Depends(auth_utils.get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
    )
