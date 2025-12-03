import asyncio
import io
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import pdfplumber
import pytesseract
from langchain.chat_models import init_chat_model
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, UnstructuredFileLoader
from PIL import Image

from ..config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DEFAULT_LLM_MODEL_GOOGLE,
    DEFAULT_LLM_MODEL_OPENAI,
    GOOGLE_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound document processing operations
_executor = ThreadPoolExecutor(max_workers=int(os.getenv("THREAD_POOL_SIZE", "4")))


class DocumentProcessorService:
    """Handles document loading, processing, and vector store creation."""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )
        if LLM_PROVIDER == "openai":
            self.llm = init_chat_model(
                model=DEFAULT_LLM_MODEL_OPENAI,
                model_provider="openai",
                temperature=0,
                api_key=OPENAI_API_KEY,
            )
        elif LLM_PROVIDER == "google_genai":
            self.llm = init_chat_model(
                model=DEFAULT_LLM_MODEL_GOOGLE,
                model_provider="google_genai",
                temperature=0,
                api_key=GOOGLE_API_KEY,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

        # Check if Tesseract OCR is available
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            logger.warning("Tesseract OCR not found. Image processing will be limited.")

    async def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load documents from file paths, including multi-modal documents with OCR."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._sync_load_documents, file_paths)

    async def extract_rfp_text(self, rfp_file_path: str) -> str:
        """Extract text from RFP document, including multi-modal documents with OCR."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._sync_extract_rfp_text, rfp_file_path)

    def _sync_load_documents(self, file_paths: List[str]) -> List[Document]:
        return self._load_multimodal_documents(file_paths)

    def _sync_extract_rfp_text(self, rfp_file_path: str) -> str:
        logger.info(f"Starting RFP text extraction from: {rfp_file_path}")

        try:
            if not Path(rfp_file_path).exists():
                logger.error(f"File not found: {rfp_file_path}")
                raise FileNotFoundError(f"File not found: {rfp_file_path}")

            documents = self._load_multimodal_documents([rfp_file_path])
            rfp_text = "\n\n".join([doc.page_content for doc in documents])

            if not rfp_text.strip():
                logger.warning("Extracted RFP text is empty!")

            return rfp_text

        except Exception as e:
            logger.error(f"Error extracting RFP text: {e}", exc_info=True)
            raise

    def _extract_text_from_image(self, image_bytes: bytes) -> str:
        """Extract text from image bytes using OCR."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return ""

    def _load_multimodal_documents(self, file_paths: List[str]) -> List[Document]:
        """Load documents from file paths, including processing images with OCR."""
        documents = []

        for file_path in file_paths:
            try:
                if file_path.endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()

                    total_text = "".join(doc.page_content for doc in docs).strip()

                    if not total_text:
                        logger.info("PDF appears to be image-based, using full-page OCR")
                        docs = self._extract_text_from_pdf_pages(file_path)
                    else:
                        page_image_texts = self._extract_images_from_pdf_by_page(file_path)

                        for i, doc in enumerate(docs):
                            if i < len(page_image_texts) and page_image_texts[i]:
                                doc.page_content += f"\n\n[OCR Text from Images on Page {i + 1}]:\n{page_image_texts[i]}"

                elif file_path.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif")
                ):
                    with open(file_path, "rb") as f:
                        image_bytes = f.read()
                        extracted_text = self._extract_text_from_image(image_bytes)

                        doc = Document(
                            page_content=extracted_text,
                            metadata={
                                "source_file": Path(file_path).name,
                                "file_path": file_path,
                                "file_type": "image",
                            },
                        )
                        docs = [doc]
                else:
                    loader = UnstructuredFileLoader(file_path)
                    docs = loader.load()

                for doc in docs:
                    if "source_file" not in doc.metadata:
                        doc.metadata["source_file"] = Path(file_path).name
                    if "file_path" not in doc.metadata:
                        doc.metadata["file_path"] = file_path

                documents.extend(docs)
                logger.info(f"Loaded {len(docs)} documents from {file_path}")

            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        return documents

    def _extract_images_from_pdf_by_page(self, pdf_path: str) -> List[str]:
        """Extract images per page and return list of OCR texts per page."""
        page_texts = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_image_text = []

                    if hasattr(page, "images") and page.images:
                        for img_num, image in enumerate(page.images):
                            try:
                                # Clamp bbox to page boundaries (handles floating-point drift)
                                x0 = max(0, image["x0"])
                                top = max(0, image["top"])
                                x1 = min(page.width, image["x1"])
                                bottom = min(page.height, image["bottom"])

                                # Skip if clamped bbox is invalid
                                if x1 <= x0 or bottom <= top:
                                    continue

                                cropped_page = page.within_bbox((x0, top, x1, bottom))

                                if hasattr(cropped_page, "to_image"):
                                    image_data = cropped_page.to_image()

                                    img_byte_arr = io.BytesIO()
                                    image_data.save(img_byte_arr, format="PNG")
                                    img_byte_arr = img_byte_arr.getvalue()

                                    extracted_text = self._extract_text_from_image(img_byte_arr)
                                    if extracted_text.strip():
                                        page_image_text.append(extracted_text)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to process image {img_num + 1} on page {page_num + 1}: {e}"
                                )

                    page_texts.append("\n".join(page_image_text))

        except Exception as e:
            logger.error(f"Error extracting images from PDF {pdf_path}: {e}")

        return page_texts

    def _extract_text_from_pdf_pages(self, pdf_path: str) -> List[Document]:
        """Convert each PDF page to image and extract text using OCR."""
        documents = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_image = page.to_image(resolution=300)

                        img_byte_arr = io.BytesIO()
                        page_image.save(img_byte_arr, format="PNG")
                        img_bytes = img_byte_arr.getvalue()

                        extracted_text = self._extract_text_from_image(img_bytes)

                        doc = Document(
                            page_content=extracted_text,
                            metadata={
                                "source_file": Path(pdf_path).name,
                                "file_path": pdf_path,
                                "page": page_num + 1,
                                "file_type": "pdf_ocr",
                            },
                        )
                        documents.append(doc)
                        logger.info(
                            f"OCR extracted {len(extracted_text)} characters from page {page_num + 1}"
                        )

                    except Exception as e:
                        logger.warning(f"Failed to OCR page {page_num + 1}: {e}")
                        documents.append(
                            Document(
                                page_content="",
                                metadata={
                                    "source_file": Path(pdf_path).name,
                                    "file_path": pdf_path,
                                    "page": page_num + 1,
                                    "file_type": "pdf_ocr",
                                    "error": str(e),
                                },
                            )
                        )

        except Exception as e:
            logger.error(f"Error in full-page OCR for {pdf_path}: {e}")

        return documents
