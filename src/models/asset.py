from pydantic import BaseModel

class Asset(BaseModel):
    asset_name: str
