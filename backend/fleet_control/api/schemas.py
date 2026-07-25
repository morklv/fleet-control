from pydantic import BaseModel, Field


class PositionInput(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class JobCreate(BaseModel):
    pickup: PositionInput
    dropoff: PositionInput
    priority: int = Field(default=0, ge=0, le=10)
