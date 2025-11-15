
"""
SQLAlchemy query utilities for user operations.

Provides helper functions for checking existence, inserting users, and creating OTPs.
"""

from sqlalchemy.orm import Session

def check_email_exists(db: Session, email: str, model) -> object:
    """
    Check if an email exists in the specified model table.

    Args:
        db (Session): SQLAlchemy database session.
        email (str): Email address to check.
        model (DeclarativeMeta): SQLAlchemy model class.

    Returns:
        object: The user instance if found, else None.
    """
    user = db.query(model).filter(model.email == email).first()
    return user

def check_username_exists(db: Session, user_name: str, model) -> object:
    """
    Check if a username exists in the specified model table.

    Args:
        db (Session): SQLAlchemy database session.
        user_name (str): Username to check.
        model (DeclarativeMeta): SQLAlchemy model class.

    Returns:
        object: The user instance if found, else None.
    """
    user = db.query(model).filter(model.user_name == user_name).first()
    return user

def insert_new_user(db: Session, model, kwargs: dict) -> object:
    """
    Insert a new user into the database.

    Args:
        db (Session): SQLAlchemy database session.
        model (DeclarativeMeta): SQLAlchemy model class.
        kwargs (dict): Dictionary of fields for the new user.

    Returns:
        object: The newly created user instance.
    """
    new_user = model(**kwargs)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def create_otp(db: Session, model, kwargs: dict) -> object:
    """
    Create a new OTP entry in the database.

    Args:
        db (Session): SQLAlchemy database session.
        model (DeclarativeMeta): SQLAlchemy model class for OTP.
        kwargs (dict): Dictionary of fields for the new OTP.

    Returns:
        object: The newly created OTP instance.
    """
    new_otp = model(**kwargs)
    db.add(new_otp)
    db.commit()
    db.refresh(new_otp)
    return new_otp