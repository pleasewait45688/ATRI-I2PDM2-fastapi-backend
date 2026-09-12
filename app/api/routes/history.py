import logging
from typing import List, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.dependency import get_db
from app.db.models     import UserProfile
from app.db.models.pest_result import PestResult
from app.schemas.profile       import UserProfileCreate, UserProfileRead

from datetime import datetime, timedelta, timezone, time
from collections import defaultdict 
import json, re
from zoneinfo import ZoneInfo
# from sqlalchemy import func, cast
# from sqlalchemy.types import Integer

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/profile")
def get_profile_summary(userid: str = Query(..., alias="userid"), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.line_user_id == userid).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "name": profile.name,
        "location": profile.location,
        "farm_name": profile.farm_name,
    }

@router.get("/items")
def get_history_items(
    userid: str = Query(..., alias="userid"),
    limit: int = Query(3, ge=1, le=20),
    db: Session = Depends(get_db),
):
    # 1. 試著撈資料
    try:
        rows = (
            db.query(PestResult)
            .filter(PestResult.line_user_id == userid)
            .order_by(PestResult.created_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as e:
        # 資料庫層有問題就回 500
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    # 2. 組成前端要的 list（可能是 []、[1 筆]、[2 筆]、或最多 3 筆）
    result = []
    for r in rows:
        ts = ""
        try:
            ts = r.created_at.strftime("%Y/%m/%d %H:%M")
        except:
            ts = r.created_at.isoformat()
        result.append({
            "id": r.id,
            "timestamp": ts,
            "type": "辨識結果",
            "summary": r.result,
        })

    # 3. 直接回 array
    return result

@router.get("/trend")
def get_history_trend(
    userid: str = Query(..., alias="userid"),
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    # 最近 N 天（含今天）
    # cutoff = datetime.now(timezone.utc) - timedelta(days=days - 1)
    # today_local_date = datetime.now().date()                      # ← 新增
    today_local_date = datetime.now(ZoneInfo("Asia/Taipei")).date()
    start_local_date = today_local_date - timedelta(days=days-1)  # ← 新增
    start_local = datetime.combine(start_local_date, time(0, 0))

    # 撈出這段期間該使用者的 created_at + result（字串）
    try:
        rows = (
            db.query(PestResult.created_at, PestResult.result)
            .filter(PestResult.line_user_id == userid, PestResult.created_at >= start_local)
            .order_by(PestResult.created_at)
            .all()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    # 依日期累加「總數」
    counts = defaultdict(int)
    for created_at, raw in rows:
        total = 0
        if raw:
            # 1) 試 JSON (雙引號)
            try:
                total = int(json.loads(raw).get("總數", 0))
            except Exception:
                # 2) 把單引號換成雙引號再試（針對 str(dict)）
                try:
                    total = int(json.loads(raw.replace("'", '"')).get("總數", 0))
                except Exception:
                    # 3) 最後用 regex 抓 '總數': 123
                    m = re.search(r"[\"']總數[\"']\s*:\s*(\d+)", str(raw))
                    total = int(m.group(1)) if m else 0

        day_key = created_at.date().strftime("%Y/%m/%d")
        counts[day_key] += total

    # 補滿連續 days 天（沒資料=0）
    result = []
    for i in range(days):
        # d = (cutoff + timedelta(days=i)).date()
        # ds = d.strftime("%Y/%m/%d")
        ds = (start_local_date + timedelta(days=i)).strftime("%Y/%m/%d")
        result.append({"date": ds, "count": counts.get(ds, 0)})

    return result

@router.get("/individual_trend")
def get_individual_trend(
    userid: str = Query(..., alias="userid"),
    days: int = Query(7, ge=1, le=365),
    metric: Literal["count", "density"] = "density",                  # 預設用密度
    agg: Literal["sum", "mean", "median", "max", "p95"] | None = None,# 預設隨 metric
    classes: str | None = Query(None, description="以逗號分隔，例：thrip,gnat,whitefly,other"),
    db: Session = Depends(get_db),
):
    """
    回傳最近 N 天的「逐類別」趨勢。
    形如：
    [
      {"date":"2025/08/05","values":{"thrip":1.2,"gnat":0.8,"whitefly":0.0,"other":0.3}},
      ...
    ]
    """
    # 預設聚合
    if agg is None:
        agg = "mean" if metric == "density" else "sum"

    # cutoff = datetime.now(timezone.utc) - timedelta(days=days - 1)
    # today_local_date = datetime.now().date()                      # ← 新增
    today_local_date = datetime.now(ZoneInfo("Asia/Taipei")).date()
    start_local_date = today_local_date - timedelta(days=days-1)  # ← 新增
    start_local = datetime.combine(start_local_date, time(0, 0))

    try:
        rows = (
            db.query(PestResult.created_at, PestResult.result)
            .filter(PestResult.line_user_id == userid, PestResult.created_at >= start_local)
            .order_by(PestResult.created_at)
            .all()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    # 解析 rows → 每日、每類別的值清單
    AREA_M2 = 0.03108  # TODO: 若每張面積不同，改用資料表欄位
    by_day_cls: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    all_classes: set[str] = set()

    for created_at, raw in rows:
        # 盡量寬鬆解析字串
        payload: Dict[str, int | float] = {}
        if raw:
            try:
                payload = json.loads(raw)
            except Exception:
                try:
                    payload = json.loads(str(raw).replace("'", '"'))
                except Exception:
                    # 落到 regex 只抓到總數時，也能繼續；個別類別缺就當 0
                    payload = {}

        # 取得各類別數量（排除 '總數'，其餘視為單一類別）
        cls_counts: Dict[str, float] = {}
        for k, v in payload.items():
            if k == "總數":
                continue
            if isinstance(v, (int, float)):
                cls_counts[k] = float(v)

        # 轉密度或保留數量
        if metric == "density":
            factor = (1.0 / AREA_M2) if AREA_M2 else 1.0
            cls_values = {k: v * factor for k, v in cls_counts.items()}
        else:
            cls_values = cls_counts

        day_key = created_at.date().strftime("%Y/%m/%d")
        for c, val in cls_values.items():
            by_day_cls[day_key][c].append(val)
            all_classes.add(c)

    # 允許用 query 指定要的類別；未指定時用資料中出現過的集合
    if classes:
        requested = [c.strip() for c in classes.split(",") if c.strip()]
        class_list = requested if requested else sorted(all_classes)
    else:
        class_list = sorted(all_classes)

    # 聚合器
    def reduce(vals: list[float]) -> float:
        if not vals:
            return 0.0
        if agg == "sum":    return float(sum(vals))
        if agg == "mean":   return float(sum(vals) / len(vals))
        if agg == "median":
            s = sorted(vals); n = len(s)
            return float(s[n//2]) if n % 2 else float((s[n//2-1] + s[n//2]) / 2)
        if agg == "max":    return float(max(vals))
        if agg == "p95":
            s = sorted(vals); idx = max(0, int(0.95 * (len(s) - 1)))
            return float(s[idx])
        return float(sum(vals))  # fallback

    # 組結果：補滿連續 days 天；對每個指定類別缺值補 0
    result = []
    for i in range(days):
        # d = (cutoff + timedelta(days=i)).date()
        # ds = d.strftime("%Y/%m/%d")
        ds = (start_local_date + timedelta(days=i)).strftime("%Y/%m/%d")
        values = {c: reduce(by_day_cls.get(ds, {}).get(c, [])) for c in class_list}
        result.append({"date": ds, "values": values})

    return result