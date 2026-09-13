from sqlalchemy import Column, String, Integer, TIMESTAMP, func
from app.db.database import Base

class PestResult(Base):
    __tablename__ = "pest_records"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(255), unique=True, nullable=False)         # 圖片 UUID
    image_path = Column(String(255), nullable=False)               # 儲存圖片路徑
    result = Column(String(255), nullable=False)                       # 辨識結果數量
    created_at = Column(TIMESTAMP, server_default=func.now())      # 上傳時間
