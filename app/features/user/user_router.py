from fastapi import APIRouter, Depends, status, HTTPException, Response
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.features.user import user_models, user_schema
from app.core import sql_query, utils
from fastapi.security import OAuth2PasswordRequestForm
from app.features.user.user_models import Users
from app.core.utils import get_current_user


user_router=APIRouter(
    prefix="/api/auth/user",
    tags=["User Authentication"]
)

@user_router.post('/signup', status_code=status.HTTP_201_CREATED)
async def register_user(user: user_schema.UserCreate, db: Session = Depends(get_db)) -> dict:
    """
    Register a new user and send an email verification OTP.

    Args:
        user (schema.UserCreate): The user registration data.
        db (Session): SQLAlchemy database session dependency.

    Raises:
        HTTPException: If email or username is already taken.

    Returns:
        dict: Success message indicating account creation and email verification required.
    """

    #check if email already exists
    eresult = sql_query.check_email_exists(db=db, email=user.email, model=user_models.Users)

    if eresult:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email already taken")

    # Create a new user
    user = sql_query.insert_new_user(db=db, model=user_models.Users, kwargs=user.dict())

    # Generate OTP
    otpcode = utils.generate_otp_code()

    otp_data = user_schema.OTPData(
    code=otpcode,
    email=user.email
    )

    message ="""
        <!DOCTYPE html>
        <html lang="en">
        <head>
                <meta charset="UTF-8">
                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Document</title>
        </head>
        <body>
            <div style="width: 100%; font-size: 16px; margin-top: 20px; text-align: center;">
                <h1>Email verification</h1>
                <p>Thank you for being part of TaxFix NG. Please verifiy your email {0}. using the below token:</p>
                <p>{1}</P>
                <p>Thank you once again for joining our community.</p>
            </div>
        </body>
        </html>
    """.format(user.email, otpcode)

    utils.send_email(subject="Account verification", message=message, recipient=user.email)

    sql_query.create_otp(db=db, model=user_models.UserOneTimePassword, kwargs=otp_data.dict())

    return {
        "message": "Account created successfully please verify your email."
    }


@user_router.post("/email-verification", status_code=status.HTTP_200_OK)
async def verify_user_account(otp: user_schema.OneTimePassword, response: Response, db: Session = Depends(get_db)) -> dict:
    """
    Verify a user's account using the OTP code sent to their email.

    Args:
        otp (schema.OneTimePassword): The OTP data for verification.
        response (Response): FastAPI response object.
        db (Session): SQLAlchemy database session dependency.

    Returns:
        dict: Result of the verification process.
    """
    return utils.create_verify_account(
        db=db,
        model_otp=user_models.UserOneTimePassword,
        model=user_models.Users,
        response=response,
        kwargs=otp.dict()
    )
    

@user_router.post('/login', status_code=status.HTTP_200_OK)
async def user_jwt_token_authentication(credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> dict:
    """
    Authenticate user and return JWT token on successful login.

    Args:
        credentials (OAuth2PasswordRequestForm): User login credentials (username/email and password).
        db (Session): SQLAlchemy database session dependency.

    Returns:
        dict: JWT token and user information if authentication is successful.
    """
    return utils.create_login(
        db=db,
        model=user_models.Users,
        email=credentials.username,
        password=credentials.password
    )


@user_router.post("/forget-password", status_code=status.HTTP_200_OK)
async def reset_user_password_request(req: user_schema.ForgetPassword, db: Session = Depends(get_db)) -> dict:
    """
    Initiate password reset process by sending a reset link to the user's email.

    Args:
        req (schema.ForgetPassword): The request containing the user's email.
        db (Session): SQLAlchemy database session dependency.

    Returns:
        dict: Message indicating that the reset email has been sent.
    """
    user = sql_query.check_email_exists(db=db, email=req.email, model=user_models.Users)

    if not user:
        return Response(content="User not found", status_code=status.HTTP_404_NOT_FOUND)

    token = utils.generate_otp_code()
    otp_data = user_schema.OTPData(
    code=token,
    email=user.email
    )
    subject = "Password reset request"
    recipient = user.email
    message = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
                <meta charset="UTF-8">
                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Document</title>
        </head>
        <body>
            <div style="width: 100%; font-size: 16px; margin-top: 20px; text-align: center;">
                <h1>Password Reset</h1>
                <p>You have requested a password reset with your email {0}. If this is correct, please use the otp below to reset your password:</p>
                <p>{1}</p>
                <p>If you didn't request this, you can ignore this email.</p>
                <p>Your password won't change until you use the OTP above.</p>
            </div>
        </body>
        </html>
    """.format(user.email, token)

    utils.send_email(subject=subject, message=message, recipient=recipient)
    sql_query.create_otp(db=db, model=user_models.UserOneTimePassword, kwargs=otp_data.dict())

    return {
        "message": "email to reset your password has been been sent"
    }

@user_router.post("/reset-password/request", status_code=status.HTTP_200_OK)
async def reset_password_request_authenticated(
    db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)
):
    """Authenticated endpoint to request a password reset OTP.

    This decodes the authenticated user's token (via `get_current_user`),
    generates an OTP, persists it and emails it to the user's registered email.

    The OTP can then be used with `/api/auth/user/update-password-with-otp` to set a new password.
    """
    # generate OTP and persist
    token = utils.generate_otp_code()
    otp_data = user_schema.OTPData(code=token, email=current_user.email)

    subject = "Password reset request"
    recipient = current_user.email
    message = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
                <meta charset="UTF-8">
                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Password Reset</title>
        </head>
        <body>
            <div style="width: 100%; font-size: 16px; margin-top: 20px; text-align: center;">
                <h1>Password Reset</h1>
                <p>A password reset was requested for your account {recipient}. Use the OTP below to reset your password:</p>
                <p>{token}</p>
                <p>If you didn't request this, you can ignore this email.</p>
            </div>
        </body>
        </html>
    """

    utils.send_email(subject=subject, message=message, recipient=recipient)
    sql_query.create_otp(db=db, model=user_models.UserOneTimePassword, kwargs=otp_data.dict())

    return {"message": "Password reset OTP sent to your email."}

@user_router.post("/update-password-with-otp", status_code=status.HTTP_200_OK)
async def update_password_with_otp(req: user_schema.PasswordUpdateWithOTP, db: Session = Depends(get_db)) -> dict:
    """
    Update a user's password by validating the most recent OTP for the provided email.

    Flow:
      Part of the forget password process.
    - Fetch the user by email. If not found, return 404.
    - Fetch the most recent OTP record for that email (ordered by created_at desc).
    - Verify OTP exists, is still valid, and matches the provided code.
    - Update the user's password and mark the OTP record as invalid.
    """
    # Ensure user exists
    user = sql_query.check_email_exists(db=db, email=req.email, model=user_models.Users)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get the most recent OTP for this email
    otp_record = (
        db.query(user_models.UserOneTimePassword)
        .filter(user_models.UserOneTimePassword.email == req.email)
        .order_by(user_models.UserOneTimePassword.created_at.desc())
        .first()
    )

    if not otp_record or not otp_record.is_valid or otp_record.code != req.otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    # Update password and invalidate OTP in a single transaction
    try:
        # Assigning the plain password will be handled by EncryptedType on commit
        user.password = req.new_password
        otp_record.is_valid = False
        db.add(user)
        db.add(otp_record)
        db.commit()
        return {"message": "Password updated successfully"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update password")


@user_router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(req: user_schema.ChangePassword, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)) -> dict:
    """
    Change an authenticated user's password by validating their old password.

    Body:
      - old_password: str
      - new_password: str
    """
    # Verify old password
    if not utils.verify_password(db=db, email=current_user.email, password=req.old_password, model=user_models.Users):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

    try:
        current_user.password = req.new_password
        db.add(current_user)
        db.commit()
        return {"message": "Password changed successfully"}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not change password")


@user_router.delete("/delete-account", status_code=status.HTTP_200_OK)
async def delete_app(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)) -> dict:
    """
    Delete the authenticated user's account and all associated data.

    This endpoint requires authentication. It will permanently delete the user account
    and cannot be undone.

    Returns:
        dict: Success message indicating account deletion.
    """
    try:
        # Delete the user account
        db.delete(current_user)
        db.commit()
        return {"message": "Account deleted successfully"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete account")
