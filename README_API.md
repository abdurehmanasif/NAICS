# RFP Processing FastAPI Application

A clean, modular FastAPI application for processing RFPs (Request for Proposals) with AI-powered proposal scoring and generation capabilities.

## 🏗️ Project Structure

```
app/
├── api/                     # API endpoints
│   ├── __init__.py
│   ├── scoring.py          # Proposal scoring endpoint
│   └── generation.py       # Proposal generation endpoint
├── models/                  # Pydantic models
│   ├── __init__.py
│   └── requests.py         # Request/response schemas
├── services/               # Business logic
│   ├── __init__.py
│   ├── document_processor_service.py
│   ├── proposal_scorer_service.py
│   ├── proposal_generator_service.py
│   └── rfp_workflow_service.py
├── config.py              # Configuration settings
├── fastapi_app.py         # Main FastAPI application
└── [legacy files...]      # Original files (can be removed)

run_api.py                 # Application startup script
requirements.txt           # Dependencies
README_API.md             # This file
```

## 🚀 Getting Started

### Prerequisites

1. Python 3.8 or higher
2. Required API keys in your `.env` file:
   ```
   OPENAI_API_KEY=your_openai_key
   GOOGLE_API_KEY=your_google_key
   LLM_PROVIDER=google_genai  # or openai
   ```

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the application:
   ```bash
   python run_api.py
   ```

3. Open your browser to view the API documentation:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 📡 API Endpoints

### Health Check
- **GET** `/health` - Check API health status
- **GET** `/` - API information and available endpoints

### Proposal Scoring
- **POST** `/api/v1/scoring/score-proposal`

**Request Body:**
```json
{
  "rfp_file": "path/to/rfp.pdf",
  "proposal_file": "path/to/proposal.pdf", 
  "naics_code": "541330",
  "naics_code_description": "Engineering Services"
}
```

**Response:**
```json
{
  "score": 8.5,
  "suggestion": "Strong proposal that addresses most requirements. Consider adding more detail on timeline and risk mitigation."
}
```

### Proposal Generation
- **POST** `/api/v1/generation/generate-proposal`

**Request Body:**
```json
{
  "rfp_file": "path/to/rfp.pdf",
  "knowledge_base_files": ["path/to/company_info.pdf", "path/to/past_proposals.pdf"],
  "naics_code": "541330", 
  "naics_code_description": "Engineering Services"
}
```

**Response:**
```json
{
  "output_file_path": "/path/to/generated_proposal.md",
  "message": "Proposal successfully generated and saved to /path/to/generated_proposal.md"
}
```

## 🧩 Architecture

### Services Layer
- **DocumentProcessorService**: Handles document loading and text extraction
- **ProposalScorerService**: AI-powered proposal evaluation
- **ProposalGeneratorService**: AI-powered proposal generation  
- **RFPWorkflowService**: Orchestrates the complete workflow

### API Layer
- **scoring.py**: REST endpoints for proposal scoring
- **generation.py**: REST endpoints for proposal generation
- **models/requests.py**: Pydantic schemas for request/response validation

### Configuration
- Centralized configuration in `config.py`
- Environment-based settings via `.env` file
- Support for multiple LLM providers (OpenAI, Google)

## 🛠️ Key Features

1. **Clean Architecture**: Separation of concerns with services, API, and models
2. **Type Safety**: Full Pydantic validation for requests and responses
3. **Error Handling**: Comprehensive error handling with appropriate HTTP status codes
4. **Documentation**: Auto-generated OpenAPI/Swagger documentation
5. **Logging**: Structured logging throughout the application
6. **CORS Support**: Configurable CORS for frontend integration
7. **Health Checks**: Built-in health check endpoints

## 🔧 Development

### Running in Development Mode
```bash
python run_api.py
```
This starts the server with auto-reload enabled.

### Testing the API

#### Using curl:
```bash
# Score a proposal
curl -X POST "http://localhost:8000/api/v1/scoring/score-proposal" \
  -H "Content-Type: application/json" \
  -d '{
    "rfp_file": "Documents/RFQ+W911SG-24-Q-0101_Redacted.pdf",
    "proposal_file": "data/HDEC04-16-R-0020-Lemoore Proposal.pdf",
    "naics_code": "541330",
    "naics_code_description": "Engineering Services"
  }'

# Generate a proposal  
curl -X POST "http://localhost:8000/api/v1/generation/generate-proposal" \
  -H "Content-Type: application/json" \
  -d '{
    "rfp_file": "Documents/RFQ+W911SG-24-Q-0101_Redacted.pdf",
    "knowledge_base_files": ["data/HDEC04-16-R-0020-Lemoore Proposal.pdf"],
    "naics_code": "541330",
    "naics_code_description": "Engineering Services"
  }'
```

#### Using Python requests:
```python
import requests

# Score a proposal
response = requests.post("http://localhost:8000/api/v1/scoring/score-proposal", json={
    "rfp_file": "Documents/RFQ+W911SG-24-Q-0101_Redacted.pdf",
    "proposal_file": "data/HDEC04-16-R-0020-Lemoore Proposal.pdf", 
    "naics_code": "541330",
    "naics_code_description": "Engineering Services"
})
print(response.json())
```

## 📝 Notes

- File paths in requests should be relative to the application's working directory
- The application supports PDF and other document formats via the UnstructuredFileLoader
- Generated proposals are saved as Markdown files in the `output/` directory
- API responses include comprehensive error messages for debugging

## 🔄 Migration from Legacy Code

The original functionality has been preserved but restructured:
- `main.py` functions are now in `services/rfp_workflow_service.py`
- Business logic is separated into individual service classes
- API endpoints provide the same functionality via HTTP REST interface
- All configuration remains in `config.py`

You can safely remove the original files once you've verified the new API works correctly:
- `main.py`
- `proposal_generator.py` 
- `proposal_scorer.py`
- `document_processor.py` 