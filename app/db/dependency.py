import logging
from sqlalchemy.orm import Session
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

def get_db() -> Session:
    """
    取得一個資料庫 session，請求結束後自動關閉。
    """
    try:
        db = SessionLocal()
        logger.debug("✅ 成功取得資料庫 Session")
        yield db
    except Exception as e:
        logger.error(f"❌ 資料庫 Session 發生錯誤: {e}")
        raise e
    finally:
        db.close()
        logger.debug("🔒 資料庫 Session 已關閉")
