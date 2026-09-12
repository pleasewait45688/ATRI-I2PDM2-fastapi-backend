# app/api/routes/profile.py

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.dependency import get_db
from app.db.models     import UserProfile
from app.schemas.profile       import UserProfileCreate, UserProfileRead

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/",
    response_model=UserProfileRead,
    summary="建立或更新使用者基本資料"
)
def create_or_update_profile(
    payload:    UserProfileCreate,
    userid:     str     = Query(..., description="LINE userId"),
    db:         Session = Depends(get_db),
):
    try:
        existing = db.query(UserProfile).filter_by(line_user_id=userid).first()

        if existing:
            # --- 更新流程 ---
            existing.name         = payload.name
            existing.phone        = payload.phone
            existing.location     = payload.location
            existing.farm_name    = payload.farm_name
            existing.service_unit = payload.service_unit
            db.commit()
            db.refresh(existing)
            return existing

        # --- 新建流程 ---
        obj = UserProfile(
            line_user_id=userid,
            name=payload.name,
            phone=payload.phone,
            location=payload.location,
            farm_name=payload.farm_name,
            service_unit=payload.service_unit,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upserting profile for {userid}: {e}", exc_info=True)
        raise HTTPException(500, "Could not create or update profile")


@router.get(
    "/",
    response_model=List[UserProfileRead],
    summary="取得使用者所有基本資料"
)
def list_profiles(
    userid: str     = Query(..., description="LINE userId"),
    db:     Session = Depends(get_db),
):
    try:
        return db.query(UserProfile).filter_by(line_user_id=userid).all()
    except Exception as e:
        logger.error(f"Error querying profiles for {userid}: {e}", exc_info=True)
        raise HTTPException(500, "Could not retrieve profiles")