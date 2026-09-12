# app/init_db.py

import logging
from app.db.database import Base, engine
import app.db.models  # init table cannot be deleted

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def init_database():
    try:
        logger.info("🔧 正在初始化資料表...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 資料表初始化完成")
    except Exception as e:
        logger.exception("❌ 初始化資料表失敗")
        raise

if __name__ == "__main__":
    init_database()
