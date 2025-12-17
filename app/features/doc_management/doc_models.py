import enum
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey
from sqlalchemy.sql.expression import text
from app.core.config import Base


class DocumentCategory(enum.Enum):
    income = "income"
    other_incomes = "other_incomes"
    operating_expenses = "operating_expenses"
    other_expenses = "other_expenses"
    life_insurance = "life_insurance"
    house_rent = "house_rent"
    Statutory_deductions = "Statutory_deductions"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_email = Column(String, ForeignKey("users.email", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Enum(DocumentCategory, name="document_category"), nullable=False)
    amount = Column(Float, nullable=False)
    document_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    relevant_tax_year = Column(Integer, nullable=True, index=True)

    created_at = Column(sa.TIMESTAMP(timezone=True), server_default=text('now()'))
    updated_at = Column(sa.TIMESTAMP(timezone=True), server_default=text('now()'), onupdate=text('now()'))
