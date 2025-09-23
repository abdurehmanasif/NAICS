import io
import logging
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
            logger.info("Tesseract OCR is available")
        except pytesseract.TesseractNotFoundError:
            logger.warning("Tesseract OCR not found. Image processing will be limited.")

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load documents from file paths, including multi-modal documents with OCR."""
        return self.load_multimodal_documents(file_paths)

    def extract_rfp_text(self, rfp_file_path: str) -> str:
        """Extract text from RFP document, including multi-modal documents with OCR."""
        logger.info(f"Starting RFP text extraction from: {rfp_file_path}")

        try:
            # Check if file exists
            if not Path(rfp_file_path).exists():
                logger.error(f"File not found: {rfp_file_path}")
                raise FileNotFoundError(f"File not found: {rfp_file_path}")

            logger.info(
                f"File exists, size: {Path(rfp_file_path).stat().st_size} bytes"
            )

            # Load documents using our multi-modal loader
            documents = self.load_multimodal_documents([rfp_file_path])
            rfp_text = "\n\n".join([doc.page_content for doc in documents])
            logger.info(f"Extracted RFP text length: {len(rfp_text)} characters")

            if not rfp_text.strip():
                logger.warning("Extracted RFP text is empty!")

            # Log first 500 characters for debugging
            logger.info(f"RFP text preview: {rfp_text[:500]}...")

            return rfp_text

        except Exception as e:
            logger.error(f"Error extracting RFP text: {e}", exc_info=True)
            raise

    def _extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Extract text from image bytes using OCR.

        Args:
            image_bytes: Bytes of the image to process

        Returns:
            Extracted text from the image
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return ""

    def load_multimodal_documents(self, file_paths: List[str]) -> List[Document]:
        """
        Load documents from file paths, including processing images with OCR.
        """
        documents = []

        for file_path in file_paths:
            try:
                # For PDFs, we need special handling to extract images
                if file_path.endswith(".pdf"):
                    # Use PyPDFLoader for text content
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()

                    # Check if we got meaningful text content
                    total_text = "".join(doc.page_content for doc in docs).strip()

                    if not total_text:
                        # If PyPDFLoader returned empty content, treat as image-based PDF
                        logger.info(
                            "PDF appears to be image-based, using full-page OCR"
                        )
                        docs = self._extract_text_from_pdf_pages(file_path)
                    else:
                        # Extract images from PDF and apply OCR per page
                        page_image_texts = self._extract_images_from_pdf_by_page(
                            file_path
                        )

                        # Append OCR text to corresponding pages
                        for i, doc in enumerate(docs):
                            if i < len(page_image_texts) and page_image_texts[i]:
                                doc.page_content += f"\n\n[OCR Text from Images on Page {i + 1}]:\n{page_image_texts[i]}"

                # For image files, use OCR directly
                elif file_path.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif")
                ):
                    with open(file_path, "rb") as f:
                        image_bytes = f.read()
                        extracted_text = self._extract_text_from_image(image_bytes)

                        # Create a document with the extracted text
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
                    # For other document types, use the standard loader
                    loader = UnstructuredFileLoader(file_path)
                    docs = loader.load()

                # Add file metadata
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
                                # Extract image data
                                # Note: This is a simplified approach. More complex image extraction
                                # might be needed for some PDFs
                                cropped_page = page.within_bbox(
                                    (
                                        image["x0"],
                                        image["top"],
                                        image["x1"],
                                        image["bottom"],
                                    )
                                )

                                # Check if we can get an image from the cropped page
                                if hasattr(cropped_page, "to_image"):
                                    image_data = cropped_page.to_image()

                                    # Convert to bytes for OCR
                                    img_byte_arr = io.BytesIO()
                                    image_data.save(img_byte_arr, format="PNG")
                                    img_byte_arr = img_byte_arr.getvalue()

                                    # Apply OCR
                                    extracted_text = self._extract_text_from_image(
                                        img_byte_arr
                                    )
                                    if extracted_text.strip():
                                        page_image_text.append(extracted_text)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to process image {img_num + 1} on page {page_num + 1}: {e}"
                                )

                    # Join all image texts for this page
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
                        # Convert page to image
                        page_image = page.to_image(resolution=300)

                        # Convert to bytes for OCR
                        img_byte_arr = io.BytesIO()
                        page_image.save(img_byte_arr, format="PNG")
                        img_bytes = img_byte_arr.getvalue()

                        # Extract text using OCR
                        extracted_text = self._extract_text_from_image(img_bytes)

                        # Create document for this page
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
                        # Create empty document to maintain page order
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
