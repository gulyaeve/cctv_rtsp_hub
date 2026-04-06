from typing import Optional
from pydantic import BaseModel


class CameraScheme(BaseModel):
    id: int
    classroom_id: int
    camera_ip: Optional[str] = None
    reg_ip: Optional[str] = None
    view: str
    rtsp_url: str
    rtsp_url_preview: Optional[str] = None

    class Config:
        from_attributes = True