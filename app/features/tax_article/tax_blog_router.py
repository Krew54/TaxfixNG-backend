from fastapi import (
    APIRouter,
    HTTPException
)

from datetime import datetime
import random
from openai import OpenAI
from typing import Optional
import random
from app.core.config import get_settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

settings = get_settings()
scheduler = AsyncIOScheduler()

OPENAI_API_KEY = settings.OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

LATEST_TAX_POST = {
    "topic": None,
    "content": None,
    "generated_at": None,
}

blog_router = APIRouter(
    prefix="/api/tax",
    tags=["Tax Blog"],
)

NIGERIA_TAX_TOPICS = [

    # 🔹 PERSONAL INCOME TAX ACT (PITA)
    "Personal Income Tax Act (PITA) - allowable deductions",
    "Personal Income Tax Act (PITA) - taxable income sources",
    "Personal Income Tax Act (PITA) - consolidated relief allowance explained",
    "Personal Income Tax Act (PITA) - minimum tax rules",
    "Personal Income Tax Act (PITA) - tax residency and source of income",
    "Personal Income Tax Act (PITA) - exemptions from personal income tax",
    "Personal Income Tax Act (PITA) - taxation of bonuses and allowances",
    "Personal Income Tax Act (PITA) - taxation of foreign income",
    "Personal Income Tax Act (PITA) - joint and separate tax assessment",

    # 🔹 PAYE
    "PAYE obligations for employers",
    "PAYE - employee vs employer responsibilities",
    "PAYE - monthly remittance deadlines and penalties",
    "PAYE - tax treatment of benefits-in-kind",
    "PAYE - treatment of gratuity and severance pay",

    # 🔹 COMPANIES INCOME TAX ACT (CITA)
    "Companies Income Tax Act (CITA) - tax rates and exemptions",
    "Companies Income Tax Act (CITA) - small, medium, and large company classification",
    "Companies Income Tax Act (CITA) - allowable business expenses",
    "Companies Income Tax Act (CITA) - non-allowable deductions",
    "Companies Income Tax Act (CITA) - minimum tax provisions",
    "Companies Income Tax Act (CITA) - taxation of dividends",
    "Companies Income Tax Act (CITA) - losses and loss relief rules",
    "Companies Income Tax Act (CITA) - filing deadlines and penalties",
    "Companies Income Tax Act (CITA) - turnover-based tax rules",

    # 🔹 VALUE ADDED TAX (VAT)
    "Value Added Tax (VAT) Act - taxable and exempt goods",
    "Value Added Tax (VAT) Act - VAT registration requirements",
    "Value Added Tax (VAT) Act - standard vs zero-rated supplies",
    "Value Added Tax (VAT) Act - VAT on digital and online services",
    "Value Added Tax (VAT) Act - VAT filing and remittance timelines",
    "Value Added Tax (VAT) Act - VAT penalties and interest",
    "Value Added Tax (VAT) Act - input VAT vs output VAT",

    # 🔹 WITHHOLDING TAX
    "Withholding Tax - applicable transactions",
    "Withholding Tax - rates for individuals and companies",
    "Withholding Tax - credit notes and utilization",
    "Withholding Tax - filing and remittance obligations",
    "Withholding Tax - penalties for non-remittance",

    # 🔹 CAPITAL GAINS TAX
    "Capital Gains Tax Act - chargeable assets",
    "Capital Gains Tax Act - exempt assets and transactions",
    "Capital Gains Tax Act - tax treatment of shares and securities",
    "Capital Gains Tax Act - computation of capital gains",

    # 🔹 STAMP DUTIES
    "Stamp Duties Act - digital transactions",
    "Stamp Duties Act - instruments subject to stamp duties",
    "Stamp Duties Act - stamp duty rates and timelines",

    # 🔹 FINANCE ACT & COMPLIANCE
    "Finance Act amendments - recent changes",
    "Finance Act - impact on individuals and businesses",
    "Tax penalties for late filing in Nigeria",
    "Small business tax compliance in Nigeria",
]


async def generate_tax_post(topic: str, user_request: Optional[str] = None) -> str:
    """
    Generate a tax post for a given topic using OpenAI GPT-3.5-turbo.
    """
    prompt = f"""
    Write a clear, friendly, and professional tax education post for a Nigerian audience.

    Topic: {topic}

    Requirements:
    - Use simple language
    - Explain key points clearly
    - Use bullet points
    - Include a short practical example
    - End with a helpful tip
    - Make it mobile-app friendly
    - Do NOT give legal advice
    """

    if user_request:
        prompt += f"\nAdditional request from user: {user_request}"

    # Call GPT-3.5 Turbo
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=600,
    )

    return response.choices[0].message.content.strip()


async def publish_weekly_tax_post():
    topic = random.choice(NIGERIA_TAX_TOPICS)
    content = await generate_tax_post(topic)

    LATEST_TAX_POST.update({
        "topic": topic,
        "content": content,
        "generated_at": datetime.utcnow().isoformat(),
    })

    return LATEST_TAX_POST

@scheduler.scheduled_job(
    CronTrigger(day_of_week="sun", hour=0, minute=0)
)
async def weekly_tax_job():
    await publish_weekly_tax_post()


@blog_router.on_event("startup")
async def start_scheduler():
    if not scheduler.running:
        scheduler.start()

@blog_router.get("/weekly-post")
def get_weekly_tax_post():
    if not LATEST_TAX_POST["content"]:
        raise HTTPException(status_code=404, detail="No post available yet")

    return LATEST_TAX_POST

@blog_router.post("/admin/generate-tax-post")
async def generate_tax_post_now():
    post = await publish_weekly_tax_post()
    return {"message": "Post generated", "topic": post["topic"], "content": post["content"]}