from fastapi import APIRouter, Depends, status, HTTPException, Response
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.features.profile import profile_model, profile_schema
from app.features.user.user_models import Users
from jose import JWTError, jwt
from app.core.security import oauth_schema, SECRET_KEY, ALGORITHM
from typing import Any


profile_router = APIRouter(
    prefix="/api/auth/profile",
    tags=["Profile Management"],
)


def get_current_user(bearer_token: str = Depends(oauth_schema), db: Session = Depends(get_db)):
    """Dependency that decodes the bearer token and returns the Users model instance."""
    try:
        payload = jwt.decode(bearer_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("email")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = db.query(Users).filter(Users.email == email).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@profile_router.get("/my_profile", response_model=profile_schema.ProfileOut)
def get_my_profile(current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)) -> Any:
    """Retrieve the profile for the currently authenticated user."""
    profile = db.query(profile_model.UserProfile).filter(profile_model.UserProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@profile_router.post("/", response_model=profile_schema.ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: profile_schema.ProfileBase,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Create a profile for the logged-in user. The email from the token is used.

    If a profile already exists for the user, a 400 is returned.
    """
    existing = db.query(profile_model.UserProfile).filter(profile_model.UserProfile.email == current_user.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists")

    # Build kwargs from payload but ensure we use the authenticated user's email
    data = payload.dict(exclude={"email"}, by_alias=False)

    data["email"] = current_user.email
    data["estimated_tax"] = compute_tax_liability()

    new_profile = profile_model.UserProfile(**data)
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile


@profile_router.patch("/", response_model=profile_schema.ProfileOut)
def update_profile(
    payload: profile_schema.ProfileUpdate,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Update fields on the current user's profile. Only provided fields are changed."""
    profile = db.query(profile_model.UserProfile).filter(profile_model.UserProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    updates = payload.dict(exclude_unset=True, by_alias=False)
    for key, value in updates.items():
        if key == "name":
            setattr(profile, "Name", value)
        else:
            setattr(profile, key, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@profile_router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    """Delete the profile belonging to the current user."""
    profile = db.query(profile_model.UserProfile).filter(profile_model.UserProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    db.delete(profile)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def compute_tax_liability(
    employment_income: float = 0,
    business_income: float = 0,
    investment_income: float = 0,
    other_income: float = 0,
    chargeable_gains: float = 0,
    exempt_income: float = 0,
    final_wht_income: float = 0,
    losses_allowed: float = 0,
    capital_allowances: float = 0,
    nhf: float = 0,
    nhis: float = 0,
    pension: float = 0,
    house_loan_interest: float = 0,
    life_insurance: float = 0,
    annual_rent: float = 0
):
    """
    Compute Personal Income Tax (PIT) based on Nigeria Tax Act 2025.
    """

    # 1. TOTAL INCOME (Section 28)
    total_income = (
        employment_income +
        business_income +
        investment_income +
        other_income +
        chargeable_gains -
        exempt_income -
        final_wht_income -
        losses_allowed -
        capital_allowances
    )

    if total_income < 0:
        total_income = 0

    # 2. Eligible Deductions (Section 30)
    rent_relief = min(0.20 * annual_rent, 500000)

    eligible_deductions = (
        nhf +
        nhis +
        pension +
        house_loan_interest +
        life_insurance +
        rent_relief
    )

    # 3. Chargeable Income
    chargeable_income = max(total_income - eligible_deductions, 0)

    # 4. Apply Progressive Tax (Fourth Schedule)
    tax = 0
    remaining = chargeable_income

    # Band 1: First ₦800,000 at 0%
    band = min(remaining, 800000)
    tax += band * 0
    remaining -= band
    if remaining <= 0:
        return tax

    # Band 2: Next ₦2,200,000 at 15%
    band = min(remaining, 2200000)
    tax += band * 0.15
    remaining -= band
    if remaining <= 0:
        return tax, chargeable_income, total_income, eligible_deductions

    # Band 3: Next ₦9,000,000 at 18%
    band = min(remaining, 9000000)
    tax += band * 0.18
    remaining -= band
    if remaining <= 0:
        return tax

    # Band 4: Next ₦13,000,000 at 21%
    band = min(remaining, 13000000)
    tax += band * 0.21
    remaining -= band
    if remaining <= 0:
        return tax

    # Band 5: Next ₦25,000,000 at 23%
    band = min(remaining, 25000000)
    tax += band * 0.23
    remaining -= band
    if remaining <= 0:
        return tax

    # Band 6: Above ₦50,000,000 at 25%
    tax += remaining * 0.25

    return tax
