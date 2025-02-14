import tempfile
import os
from fastapi import UploadFile
from typing import List, Dict
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import chromadb
from chromadb.config import Settings
import logging

logger = logging.getLogger(__name__)


class DocumentUploadService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.client = chromadb.HttpClient(
            host=os.getenv("CHROMA_DB_URL"),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection_name = os.getenv("COLLECTION_NAME")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )
        logger.info(
            f"DocumentUploadService initialized with collection: {self.collection_name}"
        )

    async def process_documents(self, files: List[UploadFile]) -> Dict:
        processed_docs = []

        for file in files:
            try:
                docs = await self._load_document(file)
                if docs:
                    processed_docs.extend(docs)
                    logger.info(f"Successfully processed file: {file.filename}")
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                raise

        if not processed_docs:
            logger.warning("No valid documents to process")
            raise ValueError("No valid documents to process")

        chunks = self.text_splitter.split_documents(processed_docs)
        logger.info(f"Split documents into {len(chunks)} chunks")

        try:
            vectorstore = self._get_vectorstore()
            vectorstore.add_documents(documents=chunks)
            logger.info("Successfully added documents to vector store")
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise

        return {"total_documents": len(processed_docs), "total_chunks": len(chunks)}

    async def _load_document(self, file: UploadFile):
        name, extension = os.path.splitext(file.filename)

        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=extension
            ) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name

            if extension.lower() == ".pdf":
                loader = PyPDFLoader(temp_file_path)
            elif extension.lower() == ".txt":
                loader = TextLoader(temp_file_path)
            elif extension.lower() in [".docx", ".doc"]:
                loader = Docx2txtLoader(temp_file_path)
            else:
                raise ValueError(f"Unsupported file format: {extension}")

            documents = loader.load()
            os.unlink(temp_file_path)
            return documents
        except Exception as e:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            logger.error(f"Error loading document {file.filename}: {str(e)}")
            raise ValueError(f"Error processing {file.filename}: {str(e)}")

    def _get_vectorstore(self):
        return Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
        )

    async def get_collection_status(self):
        try:
            collection = self.client.get_collection(self.collection_name)
            status = {
                "total_documents": collection.count(),
                "collection_name": self.collection_name,
            }
            logger.info(f"Retrieved collection status: {status}")
            return status
        except Exception as e:
            logger.error(f"Error getting collection status: {str(e)}")
            raise

    async def delete_collection(self):
        """Delete all documents from the collection."""
        try:
            # Recupera a contagem antes de deletar
            count_before = self.client.get_collection(self.collection_name).count()

            # Deleta a collection
            self.client.delete_collection(self.collection_name)

            # Recria a collection vazia
            self.client.create_collection(name=self.collection_name)

            logger.info(f"Collection {self.collection_name} reset successfully")
            return {"deleted_count": count_before}
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise
