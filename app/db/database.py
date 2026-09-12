import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings  # 依你的 config 寫法調整

# 設定 logger
logger = logging.getLogger(__name__)

# 建立 SQLAlchemy Engine
try:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,  # 若要印出 SQL 可改 True
        pool_pre_ping=True  # 自動檢查連線是否有效
    )
    logger.info("✅ 資料庫 Engine 建立成功")
except SQLAlchemyError as e:
    logger.error(f"❌ 建立資料庫 Engine 失敗: {e}")
    raise e

# 建立 Session 工廠（每次請求都會用）
try:
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    logger.info("✅ SessionLocal 建立成功")
except Exception as e:
    logger.error(f"❌ 建立 SessionLocal 失敗: {e}")
    raise e

Base = declarative_base()
