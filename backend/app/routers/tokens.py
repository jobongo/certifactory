from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import User
from app.models.api_token import ApiToken
from app.schemas.api_token import ApiTokenCreate, ApiTokenCreated, ApiTokenListResponse, ApiTokenResponse

router = APIRouter(prefix="/api/v1/tokens", tags=["tokens"])


@router.get("", response_model=ApiTokenListResponse)
def list_tokens(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tokens = db.query(ApiToken).filter(ApiToken.user_id == current_user.id).order_by(ApiToken.created_at.desc()).all()
    return ApiTokenListResponse(items=tokens)


@router.post("", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
def create_token(body: ApiTokenCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    raw_token = ApiToken.generate_token()
    token = ApiToken(
        user_id=current_user.id,
        name=body.name,
        token_hash=ApiToken.hash_token(raw_token),
        token_prefix=raw_token[:10],
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return ApiTokenCreated(id=token.id, name=token.name, token=raw_token, token_prefix=token.token_prefix, created_at=token.created_at)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(token_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    token = db.query(ApiToken).filter(ApiToken.id == token_id, ApiToken.user_id == current_user.id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.is_active = False
    db.commit()
