from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    model_config = {"from_attributes": True}
