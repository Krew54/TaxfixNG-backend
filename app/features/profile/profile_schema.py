from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


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
	occupation: Optional[str] = None
	date_of_birth: Optional[str] = None
	state_of_residence: Optional[str] = None
	state_tax_authority: Optional[str] = None
	NIN: Optional[str] = None
	employment_income: Optional[float] = None
    business_income: Optional[float] = None
    other_income: Optional[float] = None
    chargable_gains: Optional[float] = None
    pension_contribution: Optional[float] = None
    national_housing_fund: Optional[float] = None
    national_health_insurance_scheme: Optional[float] = None
    life_insurance_premium: Optional[float] = None
    house_rent: Optional[float] = None
    mortgage_interest: Optional[float] = None
    losses_allowable: Optional[float] = None
    capital_allowance: Optional[float] = None   
    class Config:
		# allow reading attributes from ORM objects (SQLAlchemy models)
        orm_mode = True
		# permit population using field names when exporting
        allow_population_by_field_name = True
        from_attributes = True


class ProfileUpdate(BaseModel):
	"""Schema for updating a profile: all fields optional."""

	name: Optional[str] = Field(None, alias="Name")
	phone_no: Optional[str] = None
	address: Optional[str] = None
	occupation: Optional[str] = None
	date_of_birth: Optional[str] = None
	state_of_residence: Optional[str] = None
	state_tax_authority: Optional[str] = None
	NIN: Optional[str] = None

	income: Optional[float] = None
	pension_contribution: Optional[float] = None
	national_housing_fund: Optional[float] = None
	National_health_insurance_scheme: Optional[float] = None
	life_insurance_premium: Optional[float] = None
	house_rent: Optional[float] = None
	mortgage_interest: Optional[float] = None

	class Config:
		orm_mode = True
		allow_population_by_field_name = True
		from_attributes = True


class ProfileOut(ProfileBase):
	"""Schema returned in responses. Includes timestamps."""

	date_created: Optional[datetime] = None
	date_modified: Optional[datetime] = None

	class Config:
		orm_mode = True
		allow_population_by_field_name = True
		from_attributes = True

