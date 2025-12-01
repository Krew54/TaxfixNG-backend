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

        if kwargs.password != kwargs.confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is not verified")
    
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
    otp = otp_qs.first()

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
        return {"status": "Account verified successfully", "is_verified": user.is_verified}
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Invalid OTP"}
    