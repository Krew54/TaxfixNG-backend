from fastapi import FastAPI
import uvicorn
from app.features.profile.profile_router import profile_router

app = FastAPI(
    docs_url="/docs",
    redoc_url="/redocs",
    title="TaxFix NG",
    description="TaxFix NG is a tax filing application that helps users to file their taxes easily and efficiently.",
    version="1.0",
    contact={
        "Name": "TaxFixNG",
        "website": "www.taxfixng.com",
        "email": "info@taxfixng.com",
        "Phone":"08033796049",
    }
)


app.include_router(profile_router)
# app.include_router(documentation_router)
# app.include_router(tax_compute_router)

if __name__ == "__main__":
    uvicorn.run("app.runner:app", host="0.0.0.0", port=8000, reload=True)