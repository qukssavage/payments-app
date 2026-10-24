from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

PHONE_PATTERN = r"^\+?\d{9,15}$"


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=PHONE_PATTERN, examples=["+998901234567"])
    group_name: str = Field(min_length=1, max_length=50)
    monthly_fee: int = Field(ge=0, le=1_000_000_000, description="Месячная сумма в сумах")


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    group_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    monthly_fee: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)


class Student(StudentCreate):
    id: int
    created_at: str

class PaymentCreate(BaseModel):
    student_id: int
    amount: int = Field(gt=0, le=1_000_000_000, description="Сумма в сумах")
    paid_at: date = Field(default_factory=date.today, description="Если не указана — сегодня")

    @field_validator("paid_at")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Дата оплаты не может быть в будущем")
        return value


class Payment(PaymentCreate):
    id: int

class Debtor(BaseModel):
    id: int
    name: str
    phone: str
    group_name: str
    monthly_fee: int
    paid: int
    debt: int