import pathlib
from dotenv import load_dotenv
import os

from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()


convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)


class Settings:
    db_host: str = os.environ.get('DB_HOST')
    db_port: str = os.environ.get('DB_PORT')
    db_username: str = os.environ.get('DB_USERNAME')
    db_password: str = os.environ.get("DB_PASSWORD")
    db_name: str = os.environ.get('DB_NAME')
    mail_jet_api_key: str = os.environ.get('MAIL_JET_API_KEY')
    mail_jet_api_secret_key: str = os.environ.get('MAIL_JET_API_SECRET_KEY')
    salt=os.environ.get("SALT")
    jwt_secret_key=os.environ.get("JWT_SECRET_KEY")
    jwt_algorithm=os.environ.get("JWT_ALGORITHM")
    jwt_access_token_expires=os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 30)
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY")
   


def get_settings():
    return Settings()