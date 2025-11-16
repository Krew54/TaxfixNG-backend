import sqlalchemy as sql
from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.sql.expression import text
from sqlalchemy_utils.types.encrypted.encrypted_type import EncryptedType
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


class Users(ResourceBase):
    """
    User model for individual users.

    Attributes:
        email (str): Unique email address.
        password (str): Encrypted password.
        is_verified (bool): Whether the user is verified.
        date_joined (datetime): Timestamp of account creation.
    """
    __tablename__ = "users"
    email = Column(String, unique=True, index=True, nullable=False, primary_key=True)
    password = Column(EncryptedType(String, SALT), nullable=False)
    is_verified = Column(Boolean, default=False)
    date_joined = Column(sql.TIMESTAMP(timezone=True), server_default=text('now()'))
    date_modified = Column(sql.TIMESTAMP(timezone=True), server_default=text('now()'), onupdate=text('now()'))

    # One-to-one relationship
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,     # Ensures one-to-one
        cascade="all, delete"
    )

class UserOneTimePassword(Base):
    """
    Model for storing one-time passwords (OTP) for user email verification.

    Attributes:
        id (int): Primary key.
        email (str): Foreign key to Users.
        code (str): Unique OTP code.
        is_valid (bool): Whether the OTP is valid.
        created_at (datetime): Timestamp of OTP creation.
    """
    __tablename__ = "user_otp"
    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    email = Column(String, ForeignKey("users.email", ondelete="CASCADE"))
    code = Column(String, unique=True, nullable=False)
    is_valid = Column(Boolean, default=True)
    created_at = Column(sql.TIMESTAMP(timezone=True), server_default=text('now()'))