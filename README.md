# NAICS Proposal Service

A production-grade FastAPI micro-service that leverages state-of-the-art Large Language Models (LLMs) to automate the entire Request-For-Proposal (RFP) lifecycle – from parsing complex solicitations to delivering a polished, client-ready proposal.

## ✨ Features
1. **One-Click Proposal Generation** – Provide an RFP URL plus any supporting "knowledge-base" documents (past performance, capability statements, resumes, etc.). The service writes an executive-level proposal in a single LLM call.
2. **Seamless S3 Integration** – The final proposal is rendered to a professional **DOCX** file and uploaded back to your S3 bucket. The API returns a public URL – perfect for instant download or email delivery.
3. **Proposal Scoring** – Benchmark an existing proposal against the RFP to get a 0-10 score and AI-driven improvement suggestions.
4. **Multi-Format Ingestion** – Accepts PDF, DOCX, TXT and more via LangChain loaders.
5. **Pluggable LLMs** – Bring your own **OpenAI** or **Google Generative AI** keys. Swap providers with an env var.
6. **Built-in NAICS Validation** – Supply a NAICS code/description to guide the LLM toward industry-specific compliance.
7. **Container Ready** – Minimal footprint, stateless operation – deploy to ECS, K8s, Heroku or Fly.io with zero code changes.

---

## 🗂️ Project Structure
```text
app/
 ├─ api/                       # REST endpoints (generation & scoring)
 ├─ services/                  # Core business logic
 ├─ models/                    # Pydantic schemas
 └─ ...
Documents/                    # Runtime artefacts (generated proposals, etc.)
docs/                         # Misc documentation helpers
```

## 🚀 Quick Start
### 1. Clone & Install
```bash
git clone <your-fork>
cd NAICS
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the project root:
```dotenv
# LLM Provider (openai | google_genai)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
# or
# GOOGLE_API_KEY=AIza...

# Embeddings (openai | huggingface)
EMBEDDING_PROVIDER=openai

# AWS / S3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET_NAME=my-proposal-bucket
```

### 3. Run the Service
```bash
python run_api.py  # uvicorn with reload & swagger docs
```
Access Swagger UI at `http://localhost:8000/docs`.

---

## 🌐 API Reference (v1)
| Method | Path                                    | Purpose                                   |
| ------ | --------------------------------------- | ----------------------------------------- |
| POST   | `/api/v1/generation/generate-proposal`  | Generate a proposal DOCX from an RFP      |
| POST   | `/api/v1/scoring/score-proposal`        | Score an existing proposal                |

### Generate Proposal
`POST /api/v1/generation/generate-proposal`

**Request Body**
```json5
{
  "rfp_file_url": "https://bucket.s3.amazonaws.com/rfps/rfp.pdf",
  "knowledge_base_files_urls": [
    "https://bucket.s3.amazonaws.com/kb/capability_statement.pdf",
    "https://bucket.s3.amazonaws.com/kb/team_resume.docx"
  ],
  "naics_code": "541330",                 // optional
  "naics_code_description": "Engineering Services" // optional
}
```

**Success Response (200)**
```json
{
  "public_url": "https://bucket.s3.amazonaws.com/user_123/proposal_generation/abcd1234/generated_proposal.docx",
  "message": "Proposal successfully generated and uploaded. Access it here: https://..."
}
```

### Score Proposal
`POST /api/v1/scoring/score-proposal`

**Request Body**
```json5
{
  "rfp_file_url": "https://bucket.s3.amazonaws.com/rfps/rfp.pdf",
  "proposal_file_url": "https://bucket.s3.amazonaws.com/prev/proposal.docx",
  "naics_code": "541330",
  "naics_code_description": "Engineering Services"
}
```

**Success Response (200)**
```json
{
  "score": 8.7,
  "suggestion": "Strengthen the risk-mitigation section and reference ISO-9001 compliance."
}
```

---

## 🏗️ Architecture Overview
```text
┌──────────┐      ┌─────────────────────────┐        ┌────────────┐
│  Client  ├──▶──▶  FastAPI REST Endpoints  ├──▶────▶│   S3 Bucket│
└──────────┘      │  (Generation / Scoring)│        └────────────┘
                  └─────────┬──────────────┘
                            │
                            ▼
                   RFPWorkflowService
          ┌──────────────┬──────────────┬────────────► Parses documents / uploads output
          │              │              │
          ▼              ▼              ▼
DocumentProcessor   ProposalGenerator   ProposalScorer
(extract & split)   (LLM call)          (LLM eval)
```

## 🧑‍💻 Local Development
```bash
# Run with auto-reload
python run_api.py
# Lint & format (requires pre-commit installation)
pre-commit run --all-files
```

## ✅ Testing
Unit tests are in progress – coming soon. Feel free to contribute!

## 📝 License
[MIT](LICENSE)