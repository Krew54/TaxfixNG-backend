import sqlalchemy as sql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData, ForeignKey
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.sql.expression import text
from sqlalchemy_utils.types.encrypted.encrypted_type import EncryptedType

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

SALT='f231des342w31de04546323fdre6517hfr450dd564267yt5607ggre45edr630TaxFixNG'
# SALT=get_settings().salt


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
    date_joined = Column(sql.TIMESTAMP(timezone=True), server_default=text('now()'))
    date_modified = Column(sql.TIMESTAMP(timezone=True), server_default=text('now()'), onupdate=text('now()'))


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