rom fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, EmailStr, validator
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List
import uuid, os, enum
from dotenv import load_dotenv
 
load_dotenv()
 
# ── DATABASE ──────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aubit:aubit_password@localhost:5432/aubit_db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
 
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
 
# ── MODELS ────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    user  = "user"
    admin = "admin"
 
class User(Base):
    __tablename__ = "users"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email           = Column(String, unique=True, index=True, nullable=False)
    full_name       = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role            = Column(SAEnum(UserRole), default=UserRole.user)
    is_active       = Column(Boolean, default=True)
    is_verified     = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    vault           = relationship("Vault", back_populates="user", uselist=False)
    transactions    = relationship("Transaction", back_populates="user")
 
class WaitlistEntry(Base):
    __tablename__ = "waitlist"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email       = Column(String, unique=True, index=True, nullable=False)
    name        = Column(String, nullable=True)
    source      = Column(String, default="website")
    notes       = Column(Text, nullable=True)
    is_investor = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
 
class Vault(Base):
    __tablename__ = "vaults"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    pct_gold   = Column(Float, default=25.0)
    pct_silver = Column(Float, default=25.0)
    pct_btc    = Column(Float, default=25.0)
    pct_eth    = Column(Float, default=25.0)
    val_gold   = Column(Float, default=0.0)
    val_silver = Column(Float, default=0.0)
    val_btc    = Column(Float, default=0.0)
    val_eth    = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user       = relationship("User", back_populates="vault")
 
    @property
    def total_value(self):
        return self.val_gold + self.val_silver + self.val_btc + self.val_eth
 
class Transaction(Base):
    __tablename__ = "transactions"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    merchant      = Column(String, nullable=False)
    amount_inr    = Column(Float, nullable=False)
    reward_inr    = Column(Float, nullable=False)
    reward_gold   = Column(Float, default=0.0)
    reward_silver = Column(Float, default=0.0)
    reward_btc    = Column(Float, default=0.0)
    reward_eth    = Column(Float, default=0.0)
    status        = Column(String, default="settled")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    user          = relationship("User", back_populates="transactions")
 
Base.metadata.create_all(bind=engine)
 
# ── AUTH UTILS ────────────────────────────────────────────
SECRET_KEY    = os.getenv("SECRET_KEY", "change-this-secret-aubit-2025")
ALGORITHM     = "HS256"
TOKEN_EXPIRE  = 60 * 24
 
pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
 
def hash_password(p): return pwd_context.hash(p)
def verify_password(p, h): return pwd_context.verify(p, h)
 
def create_token(data: dict):
    d = data.copy()
    d.update({"exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE)})
    return jwt.encode(d, SECRET_KEY, algorithm=ALGORITHM)
 
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    err = HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub")
        if not uid: raise err
    except JWTError:
        raise err
    user = db.query(User).filter(User.id == uid).first()
    if not user or not user.is_active: raise err
    return user
 
def require_admin(u: User = Depends(get_current_user)):
    if u.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return u
 
# ── APP ───────────────────────────────────────────────────
app = FastAPI(title="AuBit API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
 
@app.get("/")
def root(): return {"status": "AuBit API is live", "version": "1.0.0"}
 
@app.get("/health")
def health(): return {"status": "ok"}
 
# ── AUTH ROUTES ───────────────────────────────────────────
class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str
    password: str
 
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str
    role: str
 
@app.post("/auth/register", response_model=TokenOut, status_code=201, tags=["Auth"])
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(email=data.email, full_name=data.full_name, hashed_password=hash_password(data.password))
    db.add(user)
    db.flush()
    db.add(Vault(user_id=user.id))
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_token({"sub": str(user.id)}), user_id=str(user.id), full_name=user.full_name, role=user.role.value)
 
@app.post("/auth/login", response_model=TokenOut, tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    return TokenOut(access_token=create_token({"sub": str(user.id)}), user_id=str(user.id), full_name=user.full_name, role=user.role.value)
 
@app.get("/auth/me", tags=["Auth"])
def me(u: User = Depends(get_current_user)):
    return {"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": u.role.value}
 
# ── WAITLIST ROUTES ───────────────────────────────────────
class WaitlistIn(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    source: Optional[str] = "website"
    is_investor: Optional[bool] = False
    notes: Optional[str] = None
 
@app.post("/waitlist/join", status_code=201, tags=["Waitlist"])
def join_waitlist(data: WaitlistIn, db: Session = Depends(get_db)):
    if db.query(WaitlistEntry).filter(WaitlistEntry.email == data.email).first():
        raise HTTPException(400, "Email already on waitlist")
    entry = WaitlistEntry(**data.dict())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    position = db.query(WaitlistEntry).count()
    return {"id": str(entry.id), "email": entry.email, "position": position, "is_investor": entry.is_investor}
 
@app.get("/waitlist/check/{email}", tags=["Waitlist"])
def check_waitlist(email: str, db: Session = Depends(get_db)):
    entry = db.query(WaitlistEntry).filter(WaitlistEntry.email == email).first()
    if not entry: return {"on_waitlist": False}
    pos = db.query(WaitlistEntry).filter(WaitlistEntry.created_at <= entry.created_at).count()
    return {"on_waitlist": True, "position": pos, "is_investor": entry.is_investor}
 
# ── VAULT ROUTES ──────────────────────────────────────────
class AllocIn(BaseModel):
    pct_gold: float
    pct_silver: float
    pct_btc: float
    pct_eth: float
 
    @validator('pct_eth', always=True)
    def must_sum_100(cls, v, values):
        total = values.get('pct_gold', 0) + values.get('pct_silver', 0) + values.get('pct_btc', 0) + v
        if abs(total - 100.0) > 0.01: raise ValueError(f"Must sum to 100, got {total}")
        return v
 
@app.get("/vault/", tags=["Vault"])
def get_vault(u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    v = db.query(Vault).filter(Vault.user_id == u.id).first()
    if not v: raise HTTPException(404, "Vault not found")
    return {"allocation": {"gold": v.pct_gold, "silver": v.pct_silver, "btc": v.pct_btc, "eth": v.pct_eth},
            "balances": {"gold": round(v.val_gold,2), "silver": round(v.val_silver,2), "btc": round(v.val_btc,2), "eth": round(v.val_eth,2)},
            "total_inr": round(v.total_value, 2)}
 
@app.put("/vault/allocation", tags=["Vault"])
def update_allocation(data: AllocIn, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    v = db.query(Vault).filter(Vault.user_id == u.id).first()
    if not v: raise HTTPException(404, "Vault not found")
    v.pct_gold, v.pct_silver, v.pct_btc, v.pct_eth = data.pct_gold, data.pct_silver, data.pct_btc, data.pct_eth
    db.commit()
    return {"message": "Allocation updated", "allocation": {"gold": v.pct_gold, "silver": v.pct_silver, "btc": v.pct_btc, "eth": v.pct_eth}}
 
# ── REWARDS ROUTES ────────────────────────────────────────
REWARD_RATE = 0.005
 
class TxnIn(BaseModel):
    merchant: str
    amount_inr: float
 
@app.post("/rewards/transact", status_code=201, tags=["Rewards"])
def log_transaction(data: TxnIn, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.amount_inr <= 0: raise HTTPException(400, "Amount must be positive")
    v = db.query(Vault).filter(Vault.user_id == u.id).first()
    if not v: raise HTTPException(404, "Vault not found")
    reward = round(data.amount_inr * REWARD_RATE, 2)
    r_gold   = round(reward * v.pct_gold / 100, 4)
    r_silver = round(reward * v.pct_silver / 100, 4)
    r_btc    = round(reward * v.pct_btc / 100, 4)
    r_eth    = round(reward * v.pct_eth / 100, 4)
    txn = Transaction(user_id=u.id, merchant=data.merchant, amount_inr=data.amount_inr,
                      reward_inr=reward, reward_gold=r_gold, reward_silver=r_silver, reward_btc=r_btc, reward_eth=r_eth)
    db.add(txn)
    v.val_gold += r_gold; v.val_silver += r_silver; v.val_btc += r_btc; v.val_eth += r_eth
    db.commit()
    db.refresh(txn)
    return {"id": str(txn.id), "merchant": txn.merchant, "amount_inr": txn.amount_inr,
            "reward_inr": txn.reward_inr, "rewards": {"gold": r_gold, "silver": r_silver, "btc": r_btc, "eth": r_eth}}
 
@app.get("/rewards/history", tags=["Rewards"])
def get_history(limit: int = 20, offset: int = 0, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txns = db.query(Transaction).filter(Transaction.user_id == u.id).order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    return [{"id": str(t.id), "merchant": t.merchant, "amount_inr": t.amount_inr, "reward_inr": t.reward_inr, "created_at": str(t.created_at)} for t in txns]
 
@app.get("/rewards/summary", tags=["Rewards"])
def get_summary(u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txns = db.query(Transaction).filter(Transaction.user_id == u.id).all()
    return {"total_transactions": len(txns), "total_spent_inr": round(sum(t.amount_inr for t in txns), 2),
            "total_rewards_inr": round(sum(t.reward_inr for t in txns), 2), "reward_rate": "0.5%"}
 
# ── ADMIN ROUTES ──────────────────────────────────────────
@app.get("/admin/waitlist", tags=["Admin"])
def list_waitlist(investor_only: bool = False, limit: int = 100, db: Session = Depends(get_db), _=Depends(require_admin)):
    q = db.query(WaitlistEntry)
    if investor_only: q = q.filter(WaitlistEntry.is_investor == True)
    entries = q.order_by(WaitlistEntry.created_at.desc()).limit(limit).all()
    return [{"id": str(e.id), "email": e.email, "name": e.name, "is_investor": e.is_investor, "created_at": str(e.created_at)} for e in entries]
 
@app.get("/admin/users", tags=["Admin"])
def list_users(limit: int = 50, db: Session = Depends(get_db), _=Depends(require_admin)):
    users = db.query(User).limit(limit).all()
    return [{"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": u.role.value, "created_at": str(u.created_at)} for u in users]
 
@app.get("/admin/stats", tags=["Admin"])
def stats(db: Session = Depends(get_db), _=Depends(require_admin)):
    return {
        "users": {"total": db.query(User).count(), "waitlist": db.query(WaitlistEntry).count(), "investors": db.query(WaitlistEntry).filter(WaitlistEntry.is_investor==True).count()},
        "transactions": {"total": db.query(Transaction).count(), "total_spent": round(db.query(func.sum(Transaction.amount_inr)).scalar() or 0, 2), "total_rewards": round(db.query(func.sum(Transaction.reward_inr)).scalar() or 0, 2)}
    }
 
