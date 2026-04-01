from pydantic import BaseModel


class LiveResp(BaseModel):
    status: str


class ReadyResp(BaseModel):
    db: bool
    cache: bool
