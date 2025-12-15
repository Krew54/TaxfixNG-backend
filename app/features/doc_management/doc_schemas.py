from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class DocumentCategory(str, Enum):
    income = "income"
    other_incomes = "other_incomes"
    operating_expenses = "operating_expenses"
    other_expenses = "other_expenses"
    life_insurance = "life_insurance"
    house_rent = "house_rent"
    Statutory_deductions = "Statutory_deductions"


class DocumentBase(BaseModel):
    category: DocumentCategory
    amount: float
    document_name: str
    relevant_tax_year: Optional[int] = None

    class Config:
        from_attributes = True


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    category: Optional[DocumentCategory]
    amount: Optional[float]
    document_name: Optional[str]
    relevant_tax_year: Optional[int]

    class Config:
        from_attributes = True


class DocumentOut(DocumentBase):
    id: int
    user_email: str
    file_url: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    relevant_tax_year: Optional[int] = None

    class Config:
        from_attributes = True
