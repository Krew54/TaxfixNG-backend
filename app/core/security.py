
"""
JWT authentication utilities for FastAPI application.

Provides functions for creating, verifying, and decoding JWT tokens for user authentication.
"""

from fastapi.security import OAuth2PasswordBearer
from jose import JWSError, jwt
from fastapi import status, HTTPException, Depends
from app.core.config import get_settings
from datetime import datetime, timedelta
from app.features.user import user_schema

SECRET_KEY: str = get_settings().jwt_secret_key
ALGORITHM = get_settings().jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = get_settings().jwt_access_token_expires


oauth_schema = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token with expiration.

    Args:
        data (dict): Data to encode in the token payload.

    Returns:
        str: Encoded JWT token as a string.
    """
    token_data = data.copy()
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data.update({'expires': expires.isoformat()})
    print(SECRET_KEY)
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_access_token(token: str, credentials_exception: Exception, schema_model) -> object:
    """
    Verify a JWT access token and return the token data.

    Args:
        token (str): JWT token string to verify.
        credentials_exception (Exception): Exception to raise if verification fails.
        schema_model (type): Pydantic schema model for token data.

    Returns:
        object: Token data instance users.

    Raises:
        credentials_exception: If token is invalid or missing required fields.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get('user_id')

        if id is None:
            raise credentials_exception

        if isinstance(schema_model, user_schema.TokenData):
            token_data = schema_model(user_id=id)

    except JWSError:
        raise credentials_exception

    return token_data



def get_authenticated_user(token: str = Depends(oauth_schema)) -> object:
    """
    Dependency to get the currently authenticated user from JWT token.

    Args:
        token (str): JWT token from the request (injected by FastAPI Depends).

    Returns:
        object: Token data instance user.

    Raises:
        HTTPException: If token is invalid or missing.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    return verify_access_token(token, credentials_exception)


def decode_token(token: str, schema_model) -> object:
    """
    Decode a JWT token and return the token data.

    Args:
        token (str): JWT token string to decode.
        schema_model (type): Pydantic schema model for token data.

    Returns:
        object: Token data instance user.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")

        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid token or token expired")

        if isinstance(schema_model, user_schema.UserCreate):
            token_data = schema_model(email=email)
    except JWSError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid token or token expired")
    return token_data