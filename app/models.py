from pydantic import BaseModel


class PestDetectItem(BaseModel):
    image_id: str
    result: str | None = None
