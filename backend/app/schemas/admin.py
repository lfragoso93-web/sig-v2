from pydantic import BaseModel, Field


class AdminRestoreRequest(BaseModel):
    backup_filename: str = Field(min_length=1, max_length=255)
    current_password: str = Field(min_length=1, max_length=128)
