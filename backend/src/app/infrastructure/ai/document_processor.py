import hashlib
import io
from abc import ABC, abstractmethod

import pdfplumber
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.exceptions import DocumentProcessingException
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentProcessor(ABC):
    @abstractmethod
    async def extract_text(self, file_content: bytes) -> str:
        pass

    @abstractmethod
    def get_document_type(self) -> str:
        pass


class PDFProcessor(DocumentProcessor):
    async def extract_text(self, file_content: bytes) -> str:
        try:
            text_parts = []
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error("PDF extraction failed", error=str(e))
            raise DocumentProcessingException(f"Failed to extract text from PDF: {e!s}")

    def get_document_type(self) -> str:
        return "pdf"

    async def get_page_count(self, file_content: bytes) -> int:
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                return len(pdf.pages)
        except Exception:
            return 0


class DOCXProcessor(DocumentProcessor):
    async def extract_text(self, file_content: bytes) -> str:
        try:
            doc = DocxDocument(io.BytesIO(file_content))
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error("DOCX extraction failed", error=str(e))
            raise DocumentProcessingException(f"Failed to extract text from DOCX: {e!s}")

    def get_document_type(self) -> str:
        return "docx"


class TXTProcessor(DocumentProcessor):
    async def extract_text(self, file_content: bytes) -> str:
        try:
            return file_content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return file_content.decode("latin-1")
            except Exception as e:
                logger.error("TXT extraction failed", error=str(e))
                raise DocumentProcessingException(f"Failed to decode text file: {e!s}")

    def get_document_type(self) -> str:
        return "txt"


class MarkdownProcessor(DocumentProcessor):
    async def extract_text(self, file_content: bytes) -> str:
        try:
            return file_content.decode("utf-8")
        except Exception as e:
            logger.error("Markdown extraction failed", error=str(e))
            raise DocumentProcessingException(f"Failed to decode markdown file: {e!s}")

    def get_document_type(self) -> str:
        return "markdown"


class HTMLProcessor(DocumentProcessor):
    async def extract_text(self, file_content: bytes) -> str:
        try:
            html = file_content.decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator="\n", strip=True)
            return text
        except Exception as e:
            logger.error("HTML extraction failed", error=str(e))
            raise DocumentProcessingException(f"Failed to extract text from HTML: {e!s}")

    def get_document_type(self) -> str:
        return "html"


class DocumentProcessorFactory:
    _processors: dict[str, DocumentProcessor] = {
        "application/pdf": PDFProcessor(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCXProcessor(),
        "text/plain": TXTProcessor(),
        "text/markdown": MarkdownProcessor(),
        "text/html": HTMLProcessor(),
    }

    @classmethod
    def get_processor(cls, mime_type: str) -> DocumentProcessor:
        processor = cls._processors.get(mime_type)
        if not processor:
            raise DocumentProcessingException(f"No processor for mime type: {mime_type}")
        return processor

    @classmethod
    def get_supported_types(cls) -> list[str]:
        return list(cls._processors.keys())


class TextChunker:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[dict]:
        docs = self.splitter.create_documents([text], metadatas=[metadata or {}])
        chunks = []
        for i, doc in enumerate(docs):
            chunk_hash = hashlib.sha256(doc.page_content.encode()).hexdigest()[:16]
            chunks.append(
                {
                    "content": doc.page_content,
                    "chunk_index": i,
                    "token_count": len(doc.page_content.split()),
                    "metadata": {**doc.metadata, "chunk_hash": chunk_hash},
                }
            )
        return chunks


async def process_document(
    file_content: bytes,
    mime_type: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> tuple[str, int, list[dict]]:
    processor = DocumentProcessorFactory.get_processor(mime_type)
    text = await processor.extract_text(file_content)

    page_count = 0
    if isinstance(processor, PDFProcessor):
        page_count = await processor.get_page_count(file_content)

    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = chunker.chunk_text(text)

    logger.info(
        "Document processed", mime_type=mime_type, text_length=len(text), chunks=len(chunks)
    )
    return text, page_count, chunks
