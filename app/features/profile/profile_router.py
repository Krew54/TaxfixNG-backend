from fastapi import APIRouter, Depends, status, HTTPException, Response
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.features.profile import profile_model, profile_schema
from app.features.user.user_models import Users
from typing import Any
from starlette.concurrency import run_in_threadpool
from app.core.utils import get_current_user


profile_router = APIRouter(
    prefix="/api/auth/profile",
    tags=["Profile Management"],
)

def compute_tax_liability(
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

@profile_router.get("/my_profile", response_model=profile_schema.ProfileOut)
async def get_my_profile(current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)) -> Any:
    """Retrieve the profile for the currently authenticated user."""
    def _get():
        return db.query(profile_model.UserProfile).filter(profile_model.UserProfile.email == current_user.email).first()

    profile = await run_in_threadpool(_get)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@profile_router.post("/", response_model=profile_schema.ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: profile_schema.ProfileBase,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Create a profile for the logged-in user. The email from the token is used.

    If a profile already exists for the user, a 400 is returned.
    """
    def _existing():
        return db.query(profile_model.UserProfile).filter(profile_model.UserProfile.email == current_user.email).first()

    existing = await run_in_threadpool(_existing)
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

    estimated_tax = 0
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

    def _save():
        new_profile = profile_model.UserProfile(**model_kwargs)
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return new_profile

    new_profile = await run_in_threadpool(_save)
    return new_profile


@profile_router.patch("/", response_model=profile_schema.ProfileOut)
async def update_profile(
    payload: profile_schema.ProfileBase,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Update fields on the current user's profile. Only provided fields are changed."""
    def _get():
        return db.query(profile_model.UserProfile).filter(profile_model.UserProfile.email == current_user.email).first()

    profile = await run_in_threadpool(_get)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    updates = payload.dict(exclude_unset=True, by_alias=False)
    for key, value in updates.items():
        setattr(profile, key, value)

    # Recompute expected tax due when numeric tax-related fields or period change
    numeric_fields = [
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

    # Build args from updates (if provided) otherwise fall back to existing profile values
    tax_args = {}
    for k in numeric_fields:
        if k in updates:
            tax_args[k] = updates.get(k) or 0
        else:
            tax_args[k] = getattr(profile, k, 0) or 0

    # Determine period (updates take precedence)
    period_val = updates.get("period") if "period" in updates else getattr(profile, "period", profile_schema.Period.ANNUALLY)

    try:
        estimated_tax = compute_tax_liability(
            employment_income=tax_args["employment_income"],
            business_income=tax_args["business_income"],
            other_income=tax_args["other_income"],
            chargeable_gains=tax_args["chargeable_gains"],
            losses_allowed=tax_args["losses_allowed"],
            capital_allowances=tax_args["capital_allowances"],
            national_housing_fund=tax_args["national_housing_fund"],
            National_health_insurance_scheme=tax_args["National_health_insurance_scheme"],
            pension_contribution=tax_args["pension_contribution"],
            mortgage_interest=tax_args["mortgage_interest"],
            life_insurance_premium=tax_args["life_insurance_premium"],
            house_rent=tax_args["house_rent"],
            period=period_val,
        )
    except Exception:
        estimated_tax = 0

    # If period is monthly, annualize to keep stored expected tax consistent
    if period_val == profile_schema.Period.MONTHLY:
        estimated_tax = estimated_tax * 12

    # Update profile attribute for estimated tax
    try:
        setattr(profile, "estimated_tax", estimated_tax)
    except Exception:
        # If model doesn't have this attribute, silently skip setting it
        pass

    def _save():
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    profile = await run_in_threadpool(_save)
    return profile


@profile_router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    """Delete the profile belonging to the current user."""
    def _get():
        return db.query(profile_model.UserProfile).filter(profile_model.UserProfile.email == current_user.email).first()

    profile = await run_in_threadpool(_get)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    def _delete():
        db.delete(profile)
        db.commit()

    await run_in_threadpool(_delete)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@profile_router.post("/estimate_tax")
async def estimate_tax(forecast: profile_schema.Forecast) -> Any:
    """Estimate tax liability based on provided `Forecast` request body."""
    # extract values from request body (use 0 defaults if None)
    employment_income = forecast.employment_income or 0
    business_income = forecast.business_income or 0
    other_income = forecast.other_income or 0
    chargeable_gains = forecast.chargeable_gains or 0
    losses_allowed = forecast.losses_allowed or 0
    capital_allowances = forecast.capital_allowances or 0
    national_housing_fund = forecast.national_housing_fund or 0
    National_health_insurance_scheme = forecast.National_health_insurance_scheme or 0
    pension_contribution = forecast.pension_contribution or 0
    mortgage_interest = forecast.mortgage_interest or 0
    life_insurance_premium = forecast.life_insurance_premium or 0
    house_rent = forecast.house_rent or 0
    period = forecast.period or profile_schema.Period.ANNUALLY

    # compute estimated tax after applying deductions (existing logic)
    estimated_tax = compute_tax_liability(
        employment_income=employment_income,
        business_income=business_income,
        other_income=other_income,
        chargeable_gains=chargeable_gains,
        losses_allowed=losses_allowed,
        capital_allowances=capital_allowances,
        national_housing_fund=national_housing_fund,
        National_health_insurance_scheme=National_health_insurance_scheme,
        pension_contribution=pension_contribution,
        mortgage_interest=mortgage_interest,
        life_insurance_premium=life_insurance_premium,
        house_rent=house_rent,
        period=period,
    )

    # 1. Total income (before eligible deductions) using same formula as compute_tax_liability
    total_income = (
        employment_income
        + business_income
        + other_income
        + chargeable_gains
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
        "gross_tax_liability": prior_estimated_tax,
        "total_income": total_income,
        "total_deductions": total_deduction,
        "estimated_tax_due": estimated_tax,
    }




