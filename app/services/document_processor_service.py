from pathlib import Path
from typing import List, Dict
from langchain_community.document_loaders import PyPDFLoader, UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser

from ..config import (
    EMBEDDING_PROVIDER,
    EMBEDDING_MODEL_OPENAI,
    EMBEDDING_MODEL_HUGGINGFACE,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    LLM_PROVIDER,
    DEFAULT_LLM_MODEL_OPENAI,
    DEFAULT_LLM_MODEL_GOOGLE,
    VECTOR_STORE_PATH,
    GOOGLE_API_KEY,
    OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)


class DocumentProcessorService:
    """Handles document loading, processing, and vector store creation."""

    def __init__(self):
        if EMBEDDING_PROVIDER == "huggingface":
            self.embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL_HUGGINGFACE
            )
        elif EMBEDDING_PROVIDER == "openai":
            self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL_OPENAI)
        else:
            raise ValueError(f"Unsupported embedding provider: {EMBEDDING_PROVIDER}")
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

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load documents from file paths."""
        documents = []

        for file_path in file_paths:
            try:
                if file_path.endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                else:
                    loader = UnstructuredFileLoader(file_path)

                docs = loader.load()
                # Add file metadata
                for doc in docs:
                    doc.metadata["source_file"] = Path(file_path).name
                    doc.metadata["file_path"] = file_path

                documents.extend(docs)
                logger.info(f"Loaded {len(docs)} documents from {file_path}")

            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        return documents

    def generate_document_summaries(self, documents: List[Document]) -> Dict[str, str]:
        """Generate summaries for each document."""
        summaries = {}

        summary_prompt = PromptTemplate(
            input_variables=["content"],
            template="""Generate a concise 2-3 sentence summary of the following document content 
            that describes what information it contains and how it might be useful for answering 
            RFP-related questions:

            {content}

            Summary:""",
        )

        # Create the chain properly
        summary_chain = (
            {
                "content": lambda x: x["content"]
            }  # This ensures the input mapping is correct
            | summary_prompt
            | self.llm
            | StrOutputParser()
        )

        # Group documents by source file
        docs_by_file = {}
        for doc in documents:
            file_name = doc.metadata.get("source_file", "unknown")
            if file_name not in docs_by_file:
                docs_by_file[file_name] = []
            docs_by_file[file_name].append(doc.page_content)

        # Generate summary for each file
        for file_name, contents in docs_by_file.items():
            try:
                # Combine content from all pages/chunks of the same file
                combined_content = "\n\n".join(
                    contents[:5]
                )  # Use first 5 chunks to avoid token limits
                if len(combined_content) > 4000:  # Truncate if too long
                    combined_content = combined_content[:4000] + "..."

                summary = summary_chain.invoke({"content": combined_content})
                summaries[file_name] = summary.strip()
                logger.info(f"Generated summary for {file_name}")

            except Exception as e:
                logger.error(f"Error generating summary for {file_name}: {e}")
                summaries[file_name] = (
                    f"Document containing information about {file_name}"
                )

        return summaries

    def create_vector_store(
        self, documents: List[Document], persist_path: str = None
    ) -> FAISS:
        """Create and optionally persist a vector store from documents."""
        # Split documents into chunks
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Split documents into {len(chunks)} chunks")

        # Create vector store
        vector_store = FAISS.from_documents(chunks, self.embeddings)

        if persist_path:
            vector_store.save_local(persist_path)
            logger.info(f"Vector store saved to {persist_path}")

        return vector_store

    def load_vector_store(self, persist_path: str) -> FAISS:
        """Load a persisted vector store."""
        return FAISS.load_local(
            persist_path, self.embeddings, allow_dangerous_deserialization=True
        )

    def process_knowledge_base(
        self, knowledge_base_files: List[str]
    ) -> tuple[FAISS, Dict[str, str]]:
        """Process knowledge base files and return vector store and summaries."""
        # Load documents
        documents = self.load_documents(knowledge_base_files)

        # Generate summaries
        summaries = self.generate_document_summaries(documents)

        # Create vector store
        vector_store = self.create_vector_store(
            documents, persist_path=str(VECTOR_STORE_PATH)
        )

        return vector_store, summaries

    def extract_rfp_text(self, rfp_file_path: str) -> str:
        """Extract text from RFP document."""
        logger.info(f"Starting RFP text extraction from: {rfp_file_path}")

        try:
            # Check if file exists
            if not Path(rfp_file_path).exists():
                logger.error(f"File not found: {rfp_file_path}")
                raise FileNotFoundError(f"File not found: {rfp_file_path}")

            logger.info(
                f"File exists, size: {Path(rfp_file_path).stat().st_size} bytes"
            )

            if rfp_file_path.endswith(".pdf"):
                logger.info("Using PyPDFLoader for PDF file")
                loader = PyPDFLoader(rfp_file_path)
            else:
                logger.info("Using UnstructuredFileLoader for non-PDF file")
                loader = UnstructuredFileLoader(rfp_file_path)

            logger.info("Loading documents...")
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} document pages/chunks")

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
