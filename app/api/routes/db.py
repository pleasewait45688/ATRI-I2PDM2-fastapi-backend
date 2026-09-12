from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    """
    測試與資料庫的連線是否成功。
    """
    try:
        db.execute(text("SELECT 1"))
        logger.info("✅ 成功連接資料庫")
        return {"status": "✅ 成功連接資料庫"}
    except Exception as e:
        logger.error(f"❌ 資料庫連線失敗: {e}")
        return {"status": "❌ 無法連線", "error": str(e)}
