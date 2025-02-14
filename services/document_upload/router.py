from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
from .service import DocumentUploadService
from .schemas import DocumentUploadResponse, DeleteResponse

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...), service: DocumentUploadService = Depends()
):
    """Upload multiple documents to the vector database."""
    try:
        result = await service.process_documents(files)
        return DocumentUploadResponse(
            message="Documents processed successfully",
            total_documents=result["total_documents"],
            total_chunks=result["total_chunks"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_collection_status(service: DocumentUploadService = Depends()):
    """Get status of the document collection."""
    try:
        status = await service.get_collection_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/", response_model=DeleteResponse)
async def delete_collection(service: DocumentUploadService = Depends()):
    """Delete all documents from the collection."""
    try:
        result = await service.delete_collection()
        return DeleteResponse(
            message="Collection deleted successfully",
            deleted_count=result["deleted_count"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
