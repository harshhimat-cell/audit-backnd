from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from database import get_db
from auth_utils import get_current_user
import models

router = APIRouter()

class AllocationUpdate(BaseModel):
    pct_gold:   float
    pct_silver: float
    pct_btc:    float
    pct_eth:    float

    @validator('pct_eth', always=True)
    def must_sum_to_100(cls, pct_eth, values):
        total = values.get('pct_gold', 0) + values.get('pct_silver', 0) + values.get('pct_btc', 0) + pct_eth
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Allocations must sum to 100. Got {total}")
        return pct_eth

class VaultResponse(BaseModel):
    allocation: dict
    balances:   dict
    total_inr:  float

@router.get("/", response_model=VaultResponse)
def get_vault(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vault = db.query(models.Vault).filter(models.Vault.user_id == current_user.id).first()
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    return VaultResponse(
        allocation={
            "gold":   vault.pct_gold,
            "silver": vault.pct_silver,
            "btc":    vault.pct_btc,
            "eth":    vault.pct_eth,
        },
        balances={
            "gold":   round(vault.val_gold, 2),
            "silver": round(vault.val_silver, 2),
            "btc":    round(vault.val_btc, 2),
            "eth":    round(vault.val_eth, 2),
        },
        total_inr=round(vault.total_value, 2)
    )

@router.put("/allocation", response_model=VaultResponse)
def update_allocation(
    data: AllocationUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vault = db.query(models.Vault).filter(models.Vault.user_id == current_user.id).first()
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    vault.pct_gold   = data.pct_gold
    vault.pct_silver = data.pct_silver
    vault.pct_btc    = data.pct_btc
    vault.pct_eth    = data.pct_eth
    db.commit()
    db.refresh(vault)

    return VaultResponse(
        allocation={"gold": vault.pct_gold, "silver": vault.pct_silver, "btc": vault.pct_btc, "eth": vault.pct_eth},
        balances={"gold": round(vault.val_gold, 2), "silver": round(vault.val_silver, 2), "btc": round(vault.val_btc, 2), "eth": round(vault.val_eth, 2)},
        total_inr=round(vault.total_value, 2)
    )
