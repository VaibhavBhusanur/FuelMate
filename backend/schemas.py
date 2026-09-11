from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    
class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr


class LoginResponse(BaseModel):
    message: str
    access_token: str
    token_type: str
    user: UserResponse