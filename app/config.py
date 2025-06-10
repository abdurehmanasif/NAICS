import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv(".env", override=True)

# API Keys and Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")

# Disable LangSmith tracing if no API key is provided
if not LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGCHAIN_ENDPOINT"] = ""

# Model Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google_genai")  # google_genai or openai
EMBEDDING_PROVIDER = os.getenv(
    "EMBEDDING_PROVIDER", "huggingface"
)  # huggingface or openai
DEFAULT_LLM_MODEL_OPENAI = "gpt-4.1-mini"
DEFAULT_LLM_MODEL_GOOGLE = "gemini-2.0-flash"
EMBEDDING_MODEL_OPENAI = "text-embedding-ada-002"
EMBEDDING_MODEL_HUGGINGFACE = "all-MiniLM-L6-v2"

# Directory Configuration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
KNOWLEDGE_BASE_DIR.mkdir(exist_ok=True)

# Vector Store Configuration
VECTOR_STORE_PATH = DATA_DIR / "vector_store"
os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(BASE_DIR / "app.log"), logging.StreamHandler()],
)
