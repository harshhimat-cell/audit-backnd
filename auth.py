from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import get_db
import models

router = APIRouter()

class WaitlistJoin(BaseModel):
    email:       EmailStr
    name:        Optional[str] = None
    source:      Optional[str] = "website"
    is_investor: Optional[bool] = False
    notes:       Optional[str] = None

class WaitlistResponse(BaseModel):
    id:          str
    email:       str
    name:        Optional[str]
    is_investor: bool
    position:    int

@router.post("/join", response_model=WaitlistResponse, status_code=201)
def join_waitlist(data: WaitlistJoin, db: Session = Depends(get_db)):
    existing = db.query(models.WaitlistEntry).filter(models.WaitlistEntry.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already on waitlist")

    entry = models.WaitlistEntry(
        email       = data.email,
        name        = data.name,
        source      = data.source,
        is_investor = data.is_investor,
        notes       = data.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    position = db.query(models.WaitlistEntry).count()
    return WaitlistResponse(
        id=str(entry.id),
        email=entry.email,
        name=entry.name,
        is_investor=entry.is_investor,
        position=position
    )

@router.get("/check/{email}")
def check_waitlist(email: str, db: Session = Depends(get_db)):
    entry = db.query(models.WaitlistEntry).filter(models.WaitlistEntry.email == email).first()
    if not entry:
        return {"on_waitlist": False}
    position = db.query(models.WaitlistEntry).filter(
        models.WaitlistEntry.created_at <= entry.created_at
    ).count()
    return {"on_waitlist": True, "position": position, "is_investor": entry.is_investor}
