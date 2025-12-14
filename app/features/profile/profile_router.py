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

def compute_tax_liability(
    employment_income: float = 0,
    business_income: float = 0,
    other_income: float = 0,
    chargeable_gains: float = 0,
    final_wht_income: float = 0,
    losses_allowed: float = 0,
    capital_allowances: float = 0,
    national_housing_fund: float = 0,
    National_health_insurance_scheme: float = 0,
    pension_contribution: float = 0,
    mortgage_interest: float = 0,
    life_insurance_premium: float = 0,
    house_rent: float = 0,
    period: profile_schema.Period = profile_schema.Period.ANNUALLY
):
    """
    Compute Personal Income Tax (PIT) based on Nigeria Tax Act 2025.
    """

    # 1. TOTAL INCOME (Section 28)
    total_income = (
        employment_income +
        business_income +
        other_income +
        chargeable_gains -
        final_wht_income -
        losses_allowed -
        capital_allowances
    )

    if total_income < 0:
        total_income = 0

    # 2. Eligible Deductions (Section 30)
    if period == profile_schema.Period.MONTHLY:
        rent_relief = min(0.20 * house_rent, 500000/12)
    else:
        rent_relief = min(0.20 * house_rent, 500000)

    eligible_deductions = (
        national_housing_fund +
        National_health_insurance_scheme +
        pension_contribution +
        mortgage_interest +
        life_insurance_premium +
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
        return tax

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

    # Extract tax-related inputs from payload and call compute_tax_liability
    tax_fields = [
        "employment_income",
        "business_income",
        "other_income",
        "chargeable_gains",
        "losses_allowed",
        "capital_allowances",
        "national_housing_fund",
        "National_health_insurance_scheme",
        "pension_contribution",
        "mortgage_interest",
        "life_insurance_premium",
        "house_rent",
    ]

    tax_args = {k: (getattr(payload, k, 0) or 0) for k in tax_fields}

    if tax_args:
        estimated_tax = compute_tax_liability(**tax_args)
        if payload.period == profile_schema.Period.MONTHLY:
            estimated_tax = estimated_tax * 12
    
    # Build model kwargs only with fields that exist on the UserProfile model
    model_kwargs = {}
    for attr in ("name","phone_no", "address", "occupation", "date_of_birth", "state_of_residence", "state_tax_authority", "NIN"):
        val = getattr(payload, attr, None)
        if val is not None:
            model_kwargs[attr] = val

    # ensure email is set from the authenticated user
    model_kwargs["email"] = current_user.email
    model_kwargs["estimated_tax"] = estimated_tax

    model_kwargs = model_kwargs | tax_args

    new_profile = profile_model.UserProfile(**model_kwargs)
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    # attach estimated tax to the returned object (not persisted)
    return new_profile


@profile_router.patch("/", response_model=profile_schema.ProfileOut)
def update_profile(
    payload: profile_schema.ProfileBase,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Update fields on the current user's profile. Only provided fields are changed."""
    profile = db.query(profile_model.UserProfile).filter(profile_model.UserProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    updates = payload.dict(exclude_unset=True, by_alias=False)
    for key, value in updates.items():
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


@profile_router.post("/estimate_tax")
def estimate_tax(
    employment_income: float = 0,
    business_income: float = 0,
    other_income: float = 0,
    chargeable_gains: float = 0,
    losses_allowed: float = 0,
    capital_allowances: float = 0,
    national_housing_fund: float = 0,
    National_health_insurance_scheme: float = 0,
    pension_contribution: float = 0,
    mortgage_interest: float = 0,
    life_insurance_premium: float = 0,
    house_rent: float = 0,
    period: profile_schema.Period = profile_schema.Period.ANNUALLY
) -> Any:
    """Estimate tax liability based on provided financial inputs."""
    # compute estimated tax after applying deductions (existing logic)
    estimated_tax = compute_tax_liability(
        employment_income,
        business_income,
        other_income,
        chargeable_gains,
        losses_allowed,
        capital_allowances,
        national_housing_fund,
        National_health_insurance_scheme,
        pension_contribution,
        mortgage_interest,
        life_insurance_premium,
        house_rent,
        period
    )

    # 1. Total income (before eligible deductions) using same formula as compute_tax_liability
    total_income = (
        employment_income
        + business_income
        + other_income
        + chargeable_gains
        - final_wht_income
        - losses_allowed
        - capital_allowances
    )
    if total_income < 0:
        total_income = 0

    # 2. Total deductions (eligible deductions)
    if period == profile_schema.Period.MONTHLY:
        rent_relief = min(0.20 * house_rent, 500000/12)
    else:
        rent_relief = min(0.20 * house_rent, 500000)
    total_deduction = (
        national_housing_fund
        + National_health_insurance_scheme
        + pension_contribution
        + mortgage_interest
        + life_insurance_premium
        + rent_relief
    )

    # 3. Helper to compute progressive tax on a single amount (matches compute_tax_liability bands)
    def progressive_tax(amount: float) -> float:
        tax = 0.0
        remaining = max(amount, 0)

        band = min(remaining, 800000)
        tax += band * 0
        remaining -= band
        if remaining <= 0:
            return tax

        band = min(remaining, 2200000)
        tax += band * 0.15
        remaining -= band
        if remaining <= 0:
            return tax

        band = min(remaining, 9000000)
        tax += band * 0.18
        remaining -= band
        if remaining <= 0:
            return tax

        band = min(remaining, 13000000)
        tax += band * 0.21
        remaining -= band
        if remaining <= 0:
            return tax

        band = min(remaining, 25000000)
        tax += band * 0.23
        remaining -= band
        if remaining <= 0:
            return tax

        tax += remaining * 0.25
        return tax

    # 4. prior_estimated_tax: tax calculated strictly on total_income (no eligible deductions)
    prior_estimated_tax = progressive_tax(total_income)

    # 5. estimated_tax already computed by compute_tax_liability uses deductions; keep that as final
    # Apply the same period scaling as previous behavior
    if period == profile_schema.Period.MONTHLY:
        estimated_tax = estimated_tax * 12
        prior_estimated_tax = prior_estimated_tax * 12

    # return structured forecast
    return {
        "total_income": total_income,
        "total_deduction": total_deduction,
        "prior_estimated_tax": prior_estimated_tax,
        "estimated_tax": estimated_tax,
    }




