from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid
import enum

class UserRole(str, enum.Enum):
    user  = "user"
    admin = "admin"

class AssetType(str, enum.Enum):
    gold   = "gold"
    silver = "silver"
    btc    = "btc"
    eth    = "eth"

class User(Base):
    __tablename__ = "users"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email        = Column(String, unique=True, index=True, nullable=False)
    full_name    = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role         = Column(Enum(UserRole), default=UserRole.user)
    is_active    = Column(Boolean, default=True)
    is_verified  = Column(Boolean, default=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    vault        = relationship("Vault", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")


class WaitlistEntry(Base):
    __tablename__ = "waitlist"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email      = Column(String, unique=True, index=True, nullable=False)
    name       = Column(String, nullable=True)
    source     = Column(String, default="website")   # website / referral / investor
    notes      = Column(Text, nullable=True)
    is_investor = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Vault(Base):
    __tablename__ = "vaults"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    # Allocation percentages — must sum to 100
    pct_gold   = Column(Float, default=25.0)
    pct_silver = Column(Float, default=25.0)
    pct_btc    = Column(Float, default=25.0)
    pct_eth    = Column(Float, default=25.0)
    # Accumulated asset amounts (in INR equivalent)
    val_gold   = Column(Float, default=0.0)
    val_silver = Column(Float, default=0.0)
    val_btc    = Column(Float, default=0.0)
    val_eth    = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user       = relationship("User", back_populates="vault")

    @property
    def total_value(self):
        return self.val_gold + self.val_silver + self.val_btc + self.val_eth


class Transaction(Base):
    __tablename__ = "transactions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    merchant        = Column(String, nullable=False)
    amount_inr      = Column(Float, nullable=False)   # spend amount
    reward_inr      = Column(Float, nullable=False)   # 0.5% of amount
    # Reward breakdown per asset
    reward_gold     = Column(Float, default=0.0)
    reward_silver   = Column(Float, default=0.0)
    reward_btc      = Column(Float, default=0.0)
    reward_eth      = Column(Float, default=0.0)
    status          = Column(String, default="settled")  # pending / settled
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user            = relationship("User", back_populates="transactions")
