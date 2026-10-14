# ProofLens AI — From Documents to Verifiable Answers

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16+-black.svg)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-3.8%20Flash-4285F4.svg)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/pytest-40%20passed-brightgreen.svg)]()

> **Evidence-First Document Intelligence Platform** designed to deliver verifiable, page-cited answers and cross-document comparisons grounded exclusively in source documents.

---

## 🌟 Key Features

1. **Deterministic Page Provenance:**
   - Ingests technical PDFs using `PyMuPDF` with 1-based page numbering.
   - Page-bounded token chunking (800 token windows, 120 token overlap) preserving exact source page arrays.
2. **High-Dimensional Vector Search:**
   - Vectorized using Gemini Embeddings (`gemini-embedding-2` at 768 dimensions).
   - Sub-linear approximate nearest-neighbour (ANN) retrieval powered by `pgvector` IVFFlat cosine distance indexing.
3. **Grounded Q&A with Interactive Citations:**
   - Answering powered by Gemini 3.8 Flash, conditioned on strict anti-hallucination system instructions.
   - Interactive UI citation badges (`[Page 1]`, `[Page 2]`) linking directly to verbatim source excerpts.
   - Deterministic abstention on missing or out-of-scope evidence.
4. **Cross-Document Comparison:**
   - Multi-document comparison across 2+ indexed documents along specific topics or theses.
   - Automatic relationship classification (`supports`, `differs`, `apparent_contradiction`, `not_comparable`).
5. **Modern Next.js Web Application:**
   - Next.js App Router, TypeScript, and Tailwind CSS.
   - Workspace management, real-time ingestion status polling, document viewer, and comparative synthesis dashboard.

---

## 🏗️ System Architecture

```text
[ Browser / Next.js UI ] ──(REST / JSON)──> [ FastAPI Application (Port 8000) ]
                                                    │
                   ┌────────────────────────────────┼──────────────────────────────┐
                   ▼                                ▼                              ▼
          [ Local Storage ]               [ PostgreSQL 16 ]               [ Google Gemini API ]
      (PDF byte streams on disk)       (pgvector IVFFlat ANN)       (gemini-3.8-flash & embeddings)
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.13+**
- **Node.js v20+** and **npm**
- **Docker Desktop** (for PostgreSQL + pgvector)
- **Google Gemini API Key**

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure your `GOOGLE_API_KEY` is provided in `.env`.

### 3. Start Database (PostgreSQL + pgvector)
```bash
docker compose up -d
```

### 4. Setup & Run Backend
```bash
# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -e backend

# Run database migrations
cd backend
alembic upgrade head
cd ..

# Start FastAPI development server
uvicorn prooflens.main:app --reload --host 0.0.0.0 --port 8000
```
FastAPI interactive documentation will be accessible at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Setup & Run Frontend
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing & Code Quality

### Backend Test Suite
The complete test suite runs in-memory with SQLite and deterministic stubs for Gemini APIs:
```bash
.venv\Scripts\pytest.exe backend/tests/ -v
```
*(40 passed tests covering unit extraction, chunking, embeddings, vectorization, workspaces, documents, search, QA, and comparisons)*

### Code Quality & Linting
```bash
# Backend linter (Ruff)
.venv\Scripts\ruff.exe check backend

# Frontend linter (ESLint)
cd frontend
npm run lint
```

---

## 📊 Benchmark Evaluation & Demo Seeder

### Run Evaluation Suite
A 20-case curated benchmark testing retrieval hit rate, citation validity, and abstention accuracy:
```bash
python backend/scripts/run_evaluation.py
```
**Benchmark Results:**
- Retrieval Hit Rate: `100.0%` (Target: ≥ 80%)
- Citation Validity Rate: `100.0%` (Target: 100%)
- Abstention Accuracy: `100.0%` (Target: ≥ 85%)

### Seed Demonstration Workspace
Generate synthetic technical PDFs and provision a demonstration workspace:
```bash
python backend/scripts/seed_demo.py
```

---

## 📁 Repository Structure

```text
ProofLensAI/
├── backend/
│   ├── alembic/              # Database schema migrations (001, 002)
│   ├── scripts/              # run_evaluation.py, seed_demo.py
│   ├── src/prooflens/
│   │   ├── api/v1/routes/    # health, workspaces, documents, search, analysis, comparison
│   │   ├── core/             # config, logging, exceptions, security
│   │   ├── db/models/        # workspace, document, document_page, document_chunk
│   │   ├── schemas/          # pydantic v2 validation contracts
│   │   ├── services/         # extraction, chunking, embeddings, vectorization, retrieval, llm, comparison
│   │   └── storage/          # local filesystem storage
│   └── tests/                # 40 automated tests + fixtures
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router (page.tsx, layout.tsx, globals.css)
│   │   └── lib/              # api.ts (typed API client)
├── docs/                     # PRD, TDD, and IMPLEMENTATION-PLAN
├── docker-compose.yml        # PostgreSQL 16 with pgvector extension
└── README.md
```
