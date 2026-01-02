from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class Period(str, Enum):
	ANNUALLY = "annually"
	MONTHLY = "monthly"


class ProfileBase(BaseModel):
	"""Base schema shared by create/update schemas.

	Notes:
	- The database column for the user's name is `Name` (capitalized). We expose it
	  as `name` in the API but accept the `Name` attribute when reading from the
	  ORM model.
	"""
	name: Optional[str] = Field(None, alias="Name")
	phone_no: Optional[str] = None
	address: Optional[str] = None
	employment_type: Optional[str] = None
	date_of_birth: Optional[str] = None
	state_of_residence: Optional[str] = None
	state_tax_authority: Optional[str] = None
	NIN: Optional[str] = None
	employment_income: Optional[float] = 0.0
	business_income: Optional[float] = 0.0
	other_income: Optional[float] = 0.0
	chargeable_gains: Optional[float] = 0.0
	losses_allowed: Optional[float] = 0.0
	capital_allowances: Optional[float] = 0.0

	# deduction fields (also available separately on model)
	national_housing_fund: Optional[float] = 0.0
	National_health_insurance_scheme: Optional[float] = 0.0
	pension_contribution: Optional[float] = 0.0
	voluntary_pension_contribution: Optional[float] = 0.0
	mortgage_interest: Optional[float] = 0.0
	life_insurance_premium: Optional[float] = 0.0
	house_rent: Optional[float] = 0.0
	period: Optional[Period] = Period.ANNUALLY
	estimated_tax: Optional[float] = None

	class Config:
		populate_by_name = True
		from_attributes = True


class ProfileOut(ProfileBase):
	"""Schema returned in responses. Includes timestamps."""

	date_created: Optional[datetime] = None
	date_modified: Optional[datetime] = None
	estimated_tax: Optional[float] = None

	class Config:
		populate_by_name = True
		from_attributes = True


class Forecast(BaseModel):
	"""Base schema shared by create/update schemas.

	Notes:
	- The database column for the user's name is `Name` (capitalized). We expose it
	  as `name` in the API but accept the `Name` attribute when reading from the
	  ORM model.
	"""
	employment_income: Optional[float] = 0.0
	business_income: Optional[float] = 0.0
	other_income: Optional[float] = 0.0
	chargeable_gains: Optional[float] = 0.0
	losses_allowed: Optional[float] = 0.0
	capital_allowances: Optional[float] = 0.0

	# deduction fields (also available separately on model)
	national_housing_fund: Optional[float] = 0.0
	National_health_insurance_scheme: Optional[float] = 0.0
	pension_contribution: Optional[float] = 0.0
	voluntary_pension_contribution: Optional[float] = 0.0
	mortgage_interest: Optional[float] = 0.0
	life_insurance_premium: Optional[float] = 0.0
	house_rent: Optional[float] = 0.0
	period: Optional[Period] = Period.ANNUALLY

	class Config:
		populate_by_name = True
		from_attributes = True