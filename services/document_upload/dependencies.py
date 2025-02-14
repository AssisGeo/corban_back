from .service import DocumentUploadService


async def get_document_service() -> DocumentUploadService:
    service = DocumentUploadService()
    return service
