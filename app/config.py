import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv(".env", override=True)

# ============================================================================
# API Keys and Configuration
# ============================================================================

# LLM Provider Selection (google_genai or openai)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# OpenAI API Key (required only when LLM_PROVIDER=openai)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

# Google Generative AI API Key (required only when LLM_PROVIDER=google_genai)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if LLM_PROVIDER == "google_genai" and not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=google_genai")

# LangChain/LangSmith Configuration (optional for tracing)
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")

# Thread Pool Size for blocking I/O operations
THREAD_POOL_SIZE = os.getenv("THREAD_POOL_SIZE", "4")

# Disable LangSmith tracing if no API key is provided
if not LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGCHAIN_ENDPOINT"] = ""

# ============================================================================
# Model Configuration
# ============================================================================

# Embedding Provider Selection (huggingface or openai)
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface")

# LLM Model Names
DEFAULT_LLM_MODEL_OPENAI = "gpt-4o"  # Production-ready OpenAI model
DEFAULT_LLM_MODEL_GOOGLE = "gemini-1.5-flash"  # Production-ready Google model

# Embedding Model Names
EMBEDDING_MODEL_OPENAI = "text-embedding-ada-002"
EMBEDDING_MODEL_HUGGINGFACE = "all-MiniLM-L6-v2"

# ============================================================================
# Directory Configuration
# ============================================================================

# Base directories for application data and output
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
KNOWLEDGE_BASE_DIR.mkdir(exist_ok=True)

# ============================================================================
# Vector Store Configuration
# ============================================================================

# Vector store path for document embeddings
VECTOR_STORE_PATH = DATA_DIR / "vector_store"
os.makedirs(VECTOR_STORE_PATH, exist_ok=True)

# Document chunking parameters for text splitting
CHUNK_SIZE = 1000  # Maximum characters per chunk
CHUNK_OVERLAP = 200  # Overlap between consecutive chunks

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(BASE_DIR / "app.log"), logging.StreamHandler()],
)
