
"""
SQLAlchemy query utilities for user operations.

Provides helper functions for checking existence, inserting users, and creating OTPs.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.utils import generate_otp_code
from datetime import datetime, timedelta


def purge_otps(db: Session, model, invalid_only: bool = True, older_than_hours: int = 24) -> int:
    """
    Delete OTP records older than `older_than_hours` hours.

    Args:
        db (Session): SQLAlchemy session.
        model: OTP model class (expects `created_at` and `is_valid` columns).
        invalid_only (bool): If True, only delete where `is_valid` is False. If False, delete all older records.
        older_than_hours (int): Age threshold in hours; records older than this will be removed.

    Returns:
        int: Number of rows deleted.
    """
    cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
    query = db.query(model).filter(model.created_at <= cutoff)
    if invalid_only:
        query = query.filter(model.is_valid == False)

    deleted = query.delete(synchronize_session=False)
    db.commit()

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
    # If the `code` column has a unique constraint, it's possible a generated
    # OTP collides with an existing one. Retry generation a few times on
    # IntegrityError to avoid raising an unhandled exception to ASGI.
    max_attempts = 5
    attempt = 0
    last_exc = None
    while attempt < max_attempts:
        attempt += 1
        try:
            purge_otps(db, model, invalid_only=True, older_than_hours=24)
            new_otp = model(**kwargs)
            db.add(new_otp)
            db.commit()
            db.refresh(new_otp)
            return new_otp
        except IntegrityError as exc:
            db.rollback()
            last_exc = exc
            # If it's likely a duplicate OTP code, regenerate and retry.
            msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
            if 'unique' in msg.lower() or 'duplicate' in msg.lower() or 'uq_user_otp_code' in msg:
                # regenerate code and try again
                kwargs['code'] = generate_otp_code()
                continue
            # for other integrity errors, re-raise
            raise

    # If we exhausted retries, raise the last integrity error
    if last_exc:
        raise last_exc
    return None