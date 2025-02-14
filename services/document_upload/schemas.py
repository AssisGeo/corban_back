from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    message: str
    total_documents: int
    total_chunks: int


class DeleteResponse(BaseModel):
    message: str
    deleted_count: int
