import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
import boto3
from typing import Optional

from app.core.database import get_db
from app.core.config import get_settings
from app.features.user.user_models import Users
from app.features.doc_management import doc_models, doc_schemas
from app.core.utils import get_current_user


settings = get_settings()

# Load AWS S3 configuration from env
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION") or "eu-north-1"
S3_BUCKET = os.environ.get("AWS_S3_BUCKET")


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )


def generate_signed_url(key: str, expires: int = 3600) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )


def upload_file_to_s3(file: UploadFile, key: str) -> str:
    client = get_s3_client()
    # Upload with private ACL
    client.upload_fileobj(
        file.file,
        S3_BUCKET,
        key,
        ExtraArgs={"ACL": "private", "ContentType": file.content_type},
    )

    # Construct S3 URL
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


doc_router = APIRouter(prefix="/api/documents", tags=["Document Management"])


@doc_router.post("/upload", response_model=doc_schemas.DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    category: doc_schemas.DocumentCategory = Form(...),
    document_name: str = Form(...),
    amount: float = Form(...),
    relevant_tax_year: int | None = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # validate bucket/config
    if not all([AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_BUCKET, AWS_REGION]):
        raise HTTPException(status_code=500, detail="AWS S3 configuration is missing on server")

    # generate object key
    object_key = f"documents/{current_user.email}/{uuid.uuid4().hex}_{document_name}"

    # upload in threadpool (boto3 is blocking) and get returned URL
    file_url = await run_in_threadpool(upload_file_to_s3, file, object_key)

    def _create():
        doc = doc_models.Document(
            user_email=current_user.email,
            category=doc_models.DocumentCategory(category.value),
            amount=amount,
            document_name=document_name,
            file_url=file_url,
            relevant_tax_year=relevant_tax_year,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    doc = await run_in_threadpool(_create)
    return doc


@doc_router.get("/", response_model=List[doc_schemas.DocumentOut])
async def list_documents(current_user: Users = Depends(get_current_user), db: Session = Depends(get_db), tax_year: int | None = None):
    def _get_all():
        q = db.query(doc_models.Document).filter(doc_models.Document.user_email == current_user.email)
        if tax_year is not None:
            q = q.filter(doc_models.Document.relevant_tax_year == tax_year)
        return q.all()

    docs = await run_in_threadpool(_get_all)
    return docs


@doc_router.get("/{category}", response_model=List[doc_schemas.DocumentOut])
async def list_documents_by_category(category: doc_schemas.DocumentCategory, current_user: Users = Depends(get_current_user), db: Session = Depends(get_db), tax_year: int | None = None):
    def _get_by_cat():
        q = db.query(doc_models.Document).filter(
            doc_models.Document.user_email == current_user.email,
            doc_models.Document.category == doc_models.DocumentCategory(category.value),
        )
        if tax_year is not None:
            q = q.filter(doc_models.Document.relevant_tax_year == tax_year)
        return q.all()

    docs = await run_in_threadpool(_get_by_cat)
    return docs


@doc_router.put("/{doc_id}", response_model=doc_schemas.DocumentOut)
async def update_document(
    doc_id: int,
    category: doc_schemas.DocumentCategory = Form(None),
    document_name: str = Form(None),
    amount: float = Form(None),
    relevant_tax_year: int | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def _get():
        return db.query(doc_models.Document).filter(doc_models.Document.id == doc_id).first()

    doc = await run_in_threadpool(_get)
    if not doc or doc.user_email != current_user.email:
        raise HTTPException(status_code=404, detail="Document not found")

    # If file provided, upload new file
    if file is not None:
        object_key = f"documents/{current_user.email}/{uuid.uuid4().hex}_{document_name}"
        file_url = await run_in_threadpool(upload_file_to_s3, file, object_key)
        doc.file_url = file_url

    if category is not None:
        doc.category = doc_models.DocumentCategory(category.value)
    if document_name is not None:
        doc.document_name = document_name
    if amount is not None:
        doc.amount = amount
    if relevant_tax_year is not None:
        doc.relevant_tax_year = relevant_tax_year

    def _save():
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    updated = await run_in_threadpool(_save)
    return updated


@doc_router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: int, current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)):
    def _get():
        return db.query(doc_models.Document).filter(doc_models.Document.id == doc_id).first()

    doc = await run_in_threadpool(_get)
    if not doc or doc.user_email != current_user.email:
        raise HTTPException(status_code=404, detail="Document not found")

    # attempt to delete from S3
    try:
        # file_url format: https://{bucket}.s3.{region}.amazonaws.com/{key}
        prefix = f"https://{S3_BUCKET}.s3"
        key = None
        if doc.file_url.startswith(prefix):
            key = doc.file_url.split('/', 3)[-1]
        if key:
            client = get_s3_client()
            client.delete_object(Bucket=S3_BUCKET, Key=key)
    except Exception:
        pass

    def _delete():
        db.delete(doc)
        db.commit()

    await run_in_threadpool(_delete)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})
