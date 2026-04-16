from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from auth_utils import require_admin
from typing import List, Optional
from pydantic import BaseModel
import models

router = APIRouter()

class WaitlistItem(BaseModel):
    id:          str
    email:       str
    name:        Optional[str]
    source:      str
    is_investor: bool
    notes:       Optional[str]
    created_at:  str

class UserItem(BaseModel):
    id:         str
    email:      str
    full_name:  str
    role:       str
    is_active:  bool
    created_at: str

@router.get("/waitlist", response_model=List[WaitlistItem])
def list_waitlist(
    investor_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
):
    q = db.query(models.WaitlistEntry)
    if investor_only:
        q = q.filter(models.WaitlistEntry.is_investor == True)
    entries = q.order_by(models.WaitlistEntry.created_at.desc()).offset(offset).limit(limit).all()
    return [
        WaitlistItem(
            id=str(e.id), email=e.email, name=e.name, source=e.source,
            is_investor=e.is_investor, notes=e.notes, created_at=str(e.created_at)
        ) for e in entries
    ]

@router.get("/users", response_model=List[UserItem])
def list_users(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
):
    users = db.query(models.User).offset(offset).limit(limit).all()
    return [
        UserItem(
            id=str(u.id), email=u.email, full_name=u.full_name,
            role=u.role.value, is_active=u.is_active, created_at=str(u.created_at)
        ) for u in users
    ]

@router.get("/stats")
def platform_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
):
    total_users      = db.query(models.User).count()
    total_waitlist   = db.query(models.WaitlistEntry).count()
    investor_leads   = db.query(models.WaitlistEntry).filter(models.WaitlistEntry.is_investor == True).count()
    total_txns       = db.query(models.Transaction).count()
    total_spent      = db.query(func.sum(models.Transaction.amount_inr)).scalar() or 0
    total_rewards    = db.query(func.sum(models.Transaction.reward_inr)).scalar() or 0

    return {
        "users": {
            "total":        total_users,
            "waitlist":     total_waitlist,
            "investor_leads": investor_leads,
        },
        "transactions": {
            "total":           total_txns,
            "total_spent_inr": round(total_spent, 2),
            "total_rewards_inr": round(total_rewards, 2),
        }
    }

@router.put("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    return {"message": f"User {user.email} deactivated"}
