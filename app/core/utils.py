from sqlalchemy import func
from app.core.config import get_settings
import pyotp
from mailjet_rest import Client
from app.features.user import user_models
from sqlalchemy.orm import Session
from jose import JWSError
from app.core import security
from app.core.database import get_db
from fastapi import HTTPException, Depends, status, Response
from app.core import sql_query
from app.features.user import user_schema
from jose import JWTError, jwt
from app.core.security import oauth_schema, SECRET_KEY, ALGORITHM
from app.features.user.user_models import Users


api_key = get_settings().mail_jet_api_key
api_secret = get_settings().mail_jet_api_secret_key

mailjet = Client(auth=(api_key, api_secret), version='v3.1')

def send_email(subject: str, message: str, recipient: str):
    data = {
      'Messages': [
        {
          "From": {
            "Email": "groomicatest@gmail.com",
            "Name": "TaxFix NG"
          },
          "To": [
            {
              "Email": recipient,
              "Name": "Recipient"
            }
          ],
          "Subject": subject,
          "HTMLPart": message
        }
      ]
    }
    result = mailjet.send.create(data=data)
    

secret = pyotp.random_base32()
time_otp=pyotp.TOTP(secret, interval=120)

def generate_otp_code():
    otp=time_otp.now()
    return otp

def verify_otp(code):
    return time_otp.verify(code)

def verify_password(db: Session, email:str,  password: str, model):
    user = db.query(model).filter(model.email==email).first()
    
    if user.password == password:
        return True
    return False


def reset_password(model, kwargs, db:Session=Depends(get_db)):
    try:
        response = security.decode_token(token=kwargs.get("token"), schema_model=kwargs)

        qs = db.query(model).filter(model.email == response.email)

        if not qs.first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        qs.update({"password": kwargs.password}, synchronize_session=False)
        db.commit()

        return {"message": "Password reset successful"}
    except JWSError:
        return {"message": "Token is invalid or has expired"}
    

def create_login(model, email, password, db:Session):
    user = sql_query.check_email_exists(db, email=email, model=model)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(db, email=email, password=password, model=model):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if not user.is_verified:
        # generate OTP, email to user, and persist OTP record
        try:

            otpcode = generate_otp_code()
            otp_data = user_schema.OTPData(code=otpcode, email=user.email)

            message = (
                """
                <!DOCTYPE html>
                <html lang=\"en\">
                <head>
                        <meta charset=\"UTF-8\">
                        <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\">
                        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                        <title>Account verification</title>
                </head>
                <body>
                    <div style=\"width:100%; font-size:16px; margin-top:20px; text-align:center;\">
                        <h1>Account verification</h1>
                        <p>Please verify your email {0} by using the token below:</p>
                        <p>{1}</p>
                    </div>
                </body>
                </html>
                """.format(user.email, otpcode)
            )

            send_email(subject="Account verification", message=message, recipient=user.email)
            sql_query.create_otp(db=db, model=user_models.UserOneTimePassword, kwargs=otp_data.dict())
        except Exception:
            # if email sending/creation fails, fall through to raise verification error
            pass

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is not verified. A verification OTP has been sent to your email.")
    
    access_token = security.create_access_token(data={"email": user.email})

    return {
          "access_token": access_token, 
          "token_type": "bearer"
        }

def create_verify_account(db: Session, model_otp, model, response: Response, kwargs):

    otp_qs = (
    db.query(model_otp)
    .filter(
        model_otp.code == kwargs.get('code'),
        func.lower(model_otp.email) == kwargs.get('email').lower()
        )
    )
    otp = otp_qs.order_by(model_otp.created_at.desc()).first()

    if not otp:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Invalid OTP please try again"}

    email = otp.email
  

    # is_valid = verify_otp(otp.code)
    
    if otp.is_valid:
        qs = db.query(model).filter(model.email == email)
        user = qs.first()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity")
        qs.update({"is_verified": True}, synchronize_session=False)
        otp_qs.update({"is_valid": False}, synchronize_session=False)
        db.commit()
        response.status_code = status.HTTP_200_OK
        return {"status": "Account verified successfully", "is_verified": user.is_verified}
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Invalid OTP"}
    

def get_current_user(bearer_token: str = Depends(oauth_schema), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(bearer_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = db.query(Users).filter(Users.email == email).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    