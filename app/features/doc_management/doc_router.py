import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import Optional

from app.core.database import get_db
from app.core.config import get_settings
from app.core.storage import LocalStorageManager
from app.features.user.user_models import Users
from app.features.doc_management import doc_models, doc_schemas
from app.core.utils import get_current_user


settings = get_settings()

# Initialize local storage manager
storage_manager = LocalStorageManager()


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
    # Save file if provided
    file_url = None
    if file is not None:
        try:
            # Read file content
            file_content = await file.read()
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4().hex}_{document_name}"
            
            # Save to local storage in thread pool
            relative_path = await run_in_threadpool(
                storage_manager.save_file,
                file_content,
                current_user.email,
                unique_filename
            )
            
            # Generate public URL
            file_url = storage_manager.get_public_url(relative_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )

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

    # If file provided, upload new file and delete old one
    if file is not None:
        try:
            # Delete old file if exists
            if doc.file_url:
                # Extract relative path from public URL
                if doc.file_url.startswith("/api/documents/files/"):
                    relative_path = doc.file_url.replace("/api/documents/files/", "")
                    await run_in_threadpool(storage_manager.delete_file, relative_path)
            
            # Read and save new file
            file_content = await file.read()
            unique_filename = f"{uuid.uuid4().hex}_{document_name or file.filename}"
            relative_path = await run_in_threadpool(
                storage_manager.save_file,
                file_content,
                current_user.email,
                unique_filename
            )
            
            doc.file_url = storage_manager.get_public_url(relative_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update file: {str(e)}"
            )

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

    # Delete file from local storage
    if doc.file_url:
        try:
            # Extract relative path from public URL
            if doc.file_url.startswith("/api/documents/files/"):
                relative_path = doc.file_url.replace("/api/documents/files/", "")
                await run_in_threadpool(storage_manager.delete_file, relative_path)
        except Exception:
            # Continue with database deletion even if file deletion fails
            pass

    def _delete():
        db.delete(doc)
        db.commit()

    await run_in_threadpool(_delete)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})


@doc_router.get("/files/{user_email}/{file_path:path}")
async def download_document(
    user_email: str,
    file_path: str,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download/serve a document file
    
    Security: Only allows users to download their own files
    """
    # Security check: ensure user can only access their own files
    if current_user.email != user_email:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Reconstruct relative path
    relative_path = f"{user_email}/{file_path}"
    
    # Get file path with security checks
    full_file_path = await run_in_threadpool(storage_manager.get_file_path, relative_path)
    
    if not full_file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify file is associated with a document
    def _verify_doc():
        return db.query(doc_models.Document).filter(
            doc_models.Document.user_email == current_user.email,
            doc_models.Document.file_url == f"/api/documents/files/{relative_path}"
        ).first()
    
    doc = await run_in_threadpool(_verify_doc)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Return file
    return FileResponse(
        path=full_file_path,
        filename=doc.document_name,
        media_type="application/octet-stream"
    )
