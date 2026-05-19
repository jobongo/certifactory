from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.dependencies import get_current_user, get_db
from app.models import User, AuditAction, AuditResourceType
from app.schemas.auth import LoginRequest, PasswordChange, TokenResponse, UserResponse
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
auth_service = AuthService()
audit_service = AuditService()

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not auth_service.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host
    audit_service.log(db, user.id, AuditAction.login, AuditResourceType.user, user.id, ip_address=client_ip)
    return TokenResponse(
        access_token=auth_service.create_access_token(user.id, user.role.value),
        refresh_token=auth_service.create_refresh_token(user.id, user.role.value),
    )

@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out"}

@router.put("/me/password")
def change_password(body: PasswordChange, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not auth_service.verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = auth_service.hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated"}
