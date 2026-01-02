from fastapi import FastAPI, Request
import uvicorn
from app.features.user.user_router import user_router
from app.features.profile.profile_router import profile_router
from app.features.doc_management.doc_router import doc_router
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
# from app.features.tax_article.tax_router import agent_router

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.taxfixng.com",
        "https://admin.taxfixng.com",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def add_vary_origin(request: Request, call_next):
    response = await call_next(request)
    response.headers["Vary"] = "Origin"
    return response

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


app.include_router(user_router)
app.include_router(profile_router)
app.include_router(doc_router)
# app.include_router(agent_router)

if __name__ == "__main__":
    uvicorn.run("app.runner:app", host="0.0.0.0", port=8000, reload=True)