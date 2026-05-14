from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/users", tags=["users"])
auth_service = AuthService()

@router.get("/", response_model=UserListResponse)
def list_users(page: int = Query(1, ge=1), per_page: int = Query(25, ge=1, le=100), db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.admin))):
    total = db.query(User).count()
    users = db.query(User).offset((page - 1) * per_page).limit(per_page).all()
    return UserListResponse(items=users, total=total, page=page, per_page=per_page)

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.admin))):
    if db.query(User).filter((User.username == body.username) | (User.email == body.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    user = User(username=body.username, email=body.email, password_hash=auth_service.hash_password(body.password), role=UserRole(body.role))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.admin))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, body: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.admin))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.username is not None: user.username = body.username
    if body.email is not None: user.email = body.email
    if body.role is not None: user.role = UserRole(body.role)
    if body.is_active is not None: user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.admin))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
