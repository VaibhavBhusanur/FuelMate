from fastapi import APIRouter, Depends, HTTPException, Header
from jose import JWTError
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User

from schemas import (
    SignupRequest,
    LoginRequest,
    LoginResponse
)
from utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_db():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):

    existing_user = (
        db.query(User)
        .filter(User.email == payload.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered."
        )

    new_user = User(
        name=payload.name,
        email=payload.email,
        password=hash_password(payload.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "Account created successfully.",
        "user_id": new_user.id
    }
@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):

    user = (
        db.query(User)
        .filter(User.email == payload.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    token = create_access_token(
        {
            "user_id": user.id,
            "email": user.email
        }
    )

    return {
        "message": "Login successful.",
        "access_token": token,
        "token_type": "Bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }
@router.get("/me")
def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):

    try:
        token = authorization.replace("Bearer ", "")

        payload = decode_access_token(token)

        user_id = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token."
            )

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email
    }