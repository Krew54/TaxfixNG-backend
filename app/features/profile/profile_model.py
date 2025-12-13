import sqlalchemy as sql
from sqlalchemy import ForeignKey
from sqlalchemy import Column, String
from sqlalchemy.sql.expression import text
from app.core.config import get_settings, Base
from sqlalchemy.orm import relationship

import pandas as pd

SALT=get_settings().salt


class ResourceBase(Base):
    """
    Abstract base class for all models, providing a to_dict method for serialization.

    Attributes:
        __abstract__ (bool): Indicates this is an abstract base class.
    """
    __abstract__ = True

    def to_dict(self) -> dict:
        """
        Convert model instance to dictionary, handling NaN values as None.

        Returns:
            dict: Dictionary representation of the model instance.
        """
        d = {}
        for column in self.__table__.columns:
            col_val = getattr(self, column.name)
            if pd.notna(col_val):
                d[column.name] = col_val
            else:
                d[column.name] = None
        return d


class UserProfile(ResourceBase):
    """
    UserProfile model for individual users.

    Attributes:
        name (str): Full name of the user.
        email (str): Unique email address.
        phone_no (str): Phone number of the user.
        address (str): Address of the user.
        occupation (str): Occupation of the user.
        date_of_birth (str): Date of birth of the user.
        state_of_residence (str): State of residence of the user.
        state_tax_authority (str): State tax authority of the user.
        NIN (str): National Identification Number of the user.
        employment_income (float): Employment income of the user.
        pension_contribution (float): Pension contribution of the user.
        national_housing_fund (float): National housing fund contribution of the user.
        National_health_insurance_scheme (float): National health insurance scheme contribution of the user.
        life_insurance_premium (float): Life insurance premium of the user.
        house_rent (float): House rent of the user.
        mortgage_interest (float): Mortgage interest of the user.
        estimated_tax (float): Estimated tax of the user.
        date_created (datetime): Timestamp of account creation.
        modified_at (datetime): Timestamp of last modification.
    """
    __tablename__ = "user_profile"
    
    email = Column(String, 
                   ForeignKey("users.email", ondelete="CASCADE"), 
                   unique=True, index=True, 
                   nullable=False, 
                   primary_key=True
    )
    name = Column(String, nullable=False)
    phone_no = Column(String, nullable=True)
    address = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    state_of_residence = Column(String, nullable=True)
    state_tax_authority = Column(String, nullable=True)
    NIN = Column(String, nullable=True)
    employment_income = Column(sql.Float, nullable=True)
    business_income = Column(sql.Float, nullable=True)
    other_income = Column(sql.Float, nullable=True)
    chargeable_gains = Column(sql.Float, nullable=True)
    pension_contribution = Column(sql.Float, nullable=True)
    national_housing_fund = Column(sql.Float, nullable=True)
    National_health_insurance_scheme = Column(sql.Float, nullable=True)
    life_insurance_premium = Column(sql.Float, nullable=True)
    house_rent = Column(sql.Float, nullable=True)
    mortgage_interest = Column(sql.Float, nullable=True)
    losses_allowed = Column(sql.Float, nullable=True)
    capital_allowances = Column(sql.Float, nullable=True)
    estimated_tax = Column(sql.Float, nullable=True)

    date_created = Column(sql.TIMESTAMP(timezone=True), server_default=text('now()'))
    date_modified = Column(sql.TIMESTAMP(timezone=True), server_default=text('now()'), onupdate=text('now()'))

    user = relationship("Users", back_populates="profile")