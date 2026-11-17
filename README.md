# AI-Powered Technical Viva Interview System (FastAPI)

[![CI Pipeline](https://github.com/arnav-mishra28/MLOps_End-sem-2-/actions/workflows/ci.yml/badge.svg)](https://github.com/arnav-mishra28/MLOps_End-sem-2-/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED.svg?logo=docker)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-15%20passed-brightgreen.svg)](https://pytest.org)

An automated, intelligent oral examination platform built with **FastAPI**, **Pydantic**, and **Generative AI** (Google Gemini & intelligent offline fallback engine) designed to conduct interactive technical vivas.

---

## 📌 Problem Statement & Requirements Coverage

| Requirement | Implementation Detail | Status |
| :--- | :--- | :---: |
| **FastAPI Backend** | Clean modular architecture (`app/main.py`, `app/routers/`, `app/services/`, `app/models/`) | ✅ |
| **Accept Student Details** | Accepts `student_name`, `subject`, and `difficulty_level` (Easy, Medium, Hard) | ✅ |
| **Generate First Question via LLM** | Question 1 dynamically generated based on chosen subject and difficulty level | ✅ |
| **Adaptive Evaluation & Scoring** | Evaluates student answer, scores out of 10, provides constructive feedback, and derives next question from previous responses | ✅ |
| **Session History with Unique Session ID** | Generates UUID4 session IDs and maintains conversation history per session | ✅ |
| **Exactly 3 Questions & Performance Report** | After 3 questions, generates final report with individual scores, average marks, overall assessment, and areas for improvement | ✅ |
| **Pytest Cases with Mocked LLM** | 15 comprehensive unit & integration tests, including invalid input validation and mocked LLM calls | ✅ |
| **GitHub Actions CI Workflow** | `.github/workflows/ci.yml` matrix testing across Python 3.10, 3.11, 3.12 and Docker build validation on push/PR | ✅ |
| **Containerization with Dockerfile** | Production-grade `Dockerfile` based on `python:3.11-slim` with health checks + `docker-compose.yml` | ✅ |
| **Interactive Web UI** | Modern web interface served at `/` with live progress, real-time score pills, and printable report | ✅ |

---

## 🏗️ System Architecture

```
MLOps_End-sem-2-/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Configuration & environment variable loading (.env)
│   ├── main.py                   # FastAPI initialization, CORS, static routes & health check
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic v2 data models & validation schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   └── viva.py               # API endpoints (/start, /submit-answer, /session/{id}, /sessions)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_store.py      # Thread-safe in-memory session history manager
│   │   └── llm_service.py        # Gemini API client + resilient offline mock examiner
│   └── static/
│       ├── index.html            # Interactive single-page web application
│       ├── style.css             # Responsive styling & progress indicators
│       └── app.js                # State management and API integration
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures and deterministic LLM mockers
│   ├── test_viva_api.py          # API route tests (valid & invalid inputs, full 3-question flow)
│   └── test_services.py          # Unit tests for session store and fallback engine
├── .github/
│   └── workflows/
│       └── ci.yml                # Automated CI pipeline on GitHub Actions
├── Dockerfile                    # Container definition
├── .dockerignore                 # Excluded build artifacts
├── docker-compose.yml            # Multi-container orchestration
├── .env.example                  # Environment variables template
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Production and testing dependencies
└── README.md                     # Comprehensive project documentation
```

---

## 🚀 Quickstart Guide

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/arnav-mishra28/MLOps_End-sem-2-.git
cd MLOps_End-sem-2-

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.\.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

To enable live Google Gemini LLM questions and evaluations, add your Gemini API key (obtainable for free from [Google AI Studio](https://aistudio.google.com/)):

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> **Note**: If `GEMINI_API_KEY` is not provided, the application automatically runs in **Intelligent Offline Viva Mode** with built-in technical question banks and heuristic evaluation, ensuring complete functionality without crashing or requiring API keys.

### 3. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive Web Interface**: Open [http://localhost:8000](http://localhost:8000) in your browser.
- **Interactive Swagger API Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs).
- **Alternative ReDoc**: Open [http://localhost:8000/redoc](http://localhost:8000/redoc).

---

## 📡 API Reference & Endpoints

### 1. `POST /api/viva/start`
Starts a new viva examination session and returns Question 1.

**Request Body:**
```json
{
  "student_name": "Arnav Mishra",
  "subject": "MLOps",
  "difficulty_level": "Medium"
}
```

**Response (`201 Created`):**
```json
{
  "session_id": "c7a8b65e-2f1d-4876-90c2-ea3928198f12",
  "student_name": "Arnav Mishra",
  "subject": "MLOps",
  "difficulty_level": "Medium",
  "question_number": 1,
  "total_questions": 3,
  "question": "How would you design a CI/CD pipeline for machine learning that includes automated model training, validation gates, and artifact registry pushing?",
  "message": "Welcome Arnav Mishra! Your Medium-level viva on 'MLOps' has started. Please answer Question 1."
}
```

---

### 2. `POST /api/viva/submit-answer`
Submits an answer, evaluates it with marks out of 10 and constructive feedback, and returns the next question or the final performance report.

**Request Body:**
```json
{
  "session_id": "c7a8b65e-2f1d-4876-90c2-ea3928198f12",
  "answer": "A robust CI/CD pipeline triggers on code/data changes, executes linting and unit tests, runs automated training pipelines on ephemeral runners, validates against a baseline model using threshold metrics, and pushes versioned artifacts to MLflow registry."
}
```

**Intermediate Response (Questions 1 & 2):**
```json
{
  "session_id": "c7a8b65e-2f1d-4876-90c2-ea3928198f12",
  "question_number": 1,
  "score": 8.8,
  "feedback": "Comprehensive and well-structured answer demonstrating strong technical mastery and practical insight.",
  "is_completed": false,
  "next_question": "Explain model registry workflows and the transition from candidate to production stages.",
  "report": null
}
```

**Final Response (After Question 3):**
```json
{
  "session_id": "c7a8b65e-2f1d-4876-90c2-ea3928198f12",
  "question_number": 3,
  "score": 9.2,
  "feedback": "Outstanding answer detailing container runtimes, Kubernetes operators, and distributed training.",
  "is_completed": true,
  "next_question": null,
  "report": {
    "student_name": "Arnav Mishra",
    "subject": "MLOps",
    "difficulty_level": "Medium",
    "scores": [8.8, 8.5, 9.2],
    "average_marks": 8.83,
    "overall_assessment": "Arnav Mishra demonstrated exceptional technical proficiency and articulate communication during the viva in MLOps at Medium level. The answers exhibited deep conceptual clarity, accurate terminology, and strong systematic problem-solving aptitude.",
    "areas_for_improvement": [
      "Explore cutting-edge industry standards and recent RFCs/benchmarks in MLOps",
      "Delve into advanced low-level internal optimizations and profiling techniques"
    ]
  }
}
```

---

### 3. `GET /api/viva/session/{session_id}`
Retrieves complete conversation history, all rounds of Q&A, scores, and performance report.

---

### 4. `GET /api/viva/sessions`
Returns a list of all registered sessions in the system.

---

### 5. `GET /health`
Returns health check status and system configuration:
```json
{
  "status": "healthy",
  "app_name": "AI-Powered Technical Viva Interview System",
  "llm_mode": "intelligent_offline",
  "gemini_model": "gemini-2.5-flash",
  "total_questions_per_viva": 3
}
```

---

## 🧪 Testing with Pytest

The project includes unit and integration tests covering:
- Health check and Web UI serving
- Starting viva with valid parameters
- Starting viva with invalid inputs (empty name, whitespace subject, invalid difficulty)
- Submitting answers with invalid session IDs or empty answers
- Full 3-question lifecycle end-to-end
- Rejection of answer submissions after viva completion
- Session retrieval and listing
- LLM offline mock engine & session store concurrency

All external LLM calls are mocked in the test suite so tests run completely offline and fast:

```bash
pytest -v
```

Output:
```
============================= test session starts =============================
collected 15 items

tests/test_services.py::test_session_store_lifecycle PASSED              [  6%]
tests/test_services.py::test_session_store_non_existent PASSED           [ 13%]
tests/test_services.py::test_llm_service_offline_mode PASSED             [ 20%]
tests/test_viva_api.py::test_health_check PASSED                         [ 26%]
tests/test_viva_api.py::test_root_serves_html PASSED                     [ 33%]
tests/test_viva_api.py::test_start_viva_success PASSED                   [ 40%]
tests/test_viva_api.py::test_start_viva_invalid_input_empty_name PASSED  [ 46%]
tests/test_viva_api.py::test_start_viva_invalid_input_empty_subject PASSED [ 53%]
tests/test_viva_api.py::test_start_viva_invalid_difficulty PASSED        [ 60%]
tests/test_viva_api.py::test_submit_answer_invalid_session_id PASSED     [ 66%]
tests/test_viva_api.py::test_submit_answer_empty_answer PASSED           [ 73%]
tests/test_viva_api.py::test_full_viva_lifecycle_exactly_three_questions PASSED [ 80%]
tests/test_viva_api.py::test_cannot_submit_answer_after_completion PASSED [ 86%]
tests/test_viva_api.py::test_get_session_not_found PASSED                [ 93%]
tests/test_viva_api.py::test_list_all_sessions PASSED                    [100%]

============================= 15 passed in 0.17s ==============================
```

---

## 🔄 CI/CD with GitHub Actions

The repository includes an automated GitHub Actions workflow (`.github/workflows/ci.yml`):
1. Triggers on any `push` or `pull_request` to `main` or `master`.
2. Tests the codebase across a matrix of Python versions (`3.10`, `3.11`, `3.12`).
3. Installs dependencies, compiles bytecode to verify syntax, and runs `pytest`.
4. Builds the container image via Docker Buildx to prevent container build regressions.

---

## 🐳 Docker Deployment

### Run with Docker

```bash
# Build the Docker image
docker build -t viva-interview-system:latest .

# Run container on port 8000
docker run -d -p 8000:8000 --name viva_app viva-interview-system:latest
```

### Run with Docker Compose

```bash
docker compose up -d --build
```

Access the application at [http://localhost:8000](http://localhost:8000).

---

## 🛡️ Input Validation & Error Handling

- **Pydantic v2**: String trimming, non-empty validation, enum enforcement for difficulty level (`Easy`, `Medium`, `Hard`).
- **HTTP 422**: Raised automatically for missing or malformed request payloads.
- **HTTP 404**: Raised for invalid or expired session IDs.
- **HTTP 400**: Raised if a user attempts to submit answers to a completed viva session.
- **Thread Safety**: Uses mutex locks around session history updates to prevent race conditions.

---

## 📄 License
This project is developed for academic examination and demonstration purposes.
