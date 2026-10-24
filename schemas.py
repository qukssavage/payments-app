from typing import Optional
from pydantic import BaseModel, Field

PHONE_PATTERN = r"^\+?\d{9,15}$"


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=PHONE_PATTERN, examples=["+998901234567"])
    group_name: str = Field(min_length=1, max_length=50)
    monthly_fee: int = Field(ge=0, description="Месячная сумма в сумах")


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    group_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    monthly_fee: Optional[int] = Field(default=None, ge=0)


class Student(StudentCreate):
    id: int
    created_at: str