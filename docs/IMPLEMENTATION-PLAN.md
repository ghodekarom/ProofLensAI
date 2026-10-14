# ProofLens AI — Implementation Plan

**Document ID:** PLAI-IMP-001  
**Version:** 1.0  
**Status:** Baseline Plan for Owner Approval  
**Source Baseline:** [prooflens_prd.md](file:///d:/ProofLensAI/docs/prooflens_prd.md) (PLAI-PRD-001) & [prooflens_tdd.md](file:///d:/ProofLensAI/docs/prooflens_tdd.md) (PLAI-TDD-001)  
**Execution Environment:** Windows | Python 3.13.3 | Node.js v24.19.0 / npm 11.17.0 | Docker 29.7.2  

---

## 1. Executive Summary & Implementation Philosophy

ProofLens AI is an **evidence-first document intelligence platform** designed to provide verifiable, page-cited answers from uploaded documents. 

This implementation plan breaks the project into **six sequential milestones** (following the discovery completed in Milestone 0). Each milestone produces working, testable deliverables with explicit acceptance gates. No code will be written without verifying its foundational components first.

### Key Implementation Principles:
1. **Vertical Slices Over Monolithic Scaffolding:** Each milestone completes a coherent slice of the pipeline, verified by automated unit/integration tests before proceeding.
2. **Strict Scope Discipline (No "Vibe Coding" Creep):** Zero arbitrary agents, multi-agent orchestrators (LangGraph/CrewAI/MCP), OCR, or web search in the MVP.
3. **Server-Derived Provenance:** LLM generation references evidence tokens (`E1`, `E2`), while all document metadata, page numbers, and excerpts are strictly resolved and validated server-side.
4. **Deterministic Abstention:** Insufficient or weak evidence produces an explicit `insufficient_evidence` domain response rather than hallucinated answers.

---

## 2. Technical Decisions Matrix

The following table outlines the key architectural and operational choices identified in TDD Section 19.

| # | Decision Area | Chosen Option | Details & Rationale | Status |
|---|---|---|---|---|
| **D1** | **Python Package Management** | Standard `venv` + `pip` with `pyproject.toml` | Natively compatible with Python 3.13 on Windows without external CLI dependencies. | **Confirmed by Owner** |
| **D2** | **Frontend Package Manager** | `npm` (v11.17.0) | Uses existing runtime; fast, consistent, and zero extra installation required. | **Confirmed by Owner** |
| **D3** | **Ingestion Processing Model** | FastAPI `BackgroundTasks` | Asynchronous in-process ingestion keeping file uploads responsive (<500ms) with client status polling. | **Confirmed by Owner** |
| **D4** | **Authentication & Scope** | Single-user local demo mode | Clean workspace-isolated data model; optimal for college presentation and portfolio demo without authentication friction. | **Confirmed by Owner** |
| **D5** | **Document Deletion Policy** | Hard cascade deletion | Eliminates orphaned vectors/chunks and cleanly removes physical files from storage. | **Confirmed by Owner** |
| **D6** | **AI Model Integration** | `gemini-3.8-flash` & `gemini-embedding-2` (768-dim) | Gemini API via official `google-genai` SDK, behind replaceable provider adapters. | **Confirmed by Owner** |

---

## 3. Target Repository Structure

```text
prooflens-ai/
├── docs/
│   ├── prooflens_prd.md
│   ├── prooflens_tdd.md
│   └── IMPLEMENTATION-PLAN.md
├── docker-compose.yml              # Local PostgreSQL 16 + pgvector container
├── .gitignore
├── .env.example
├── README.md
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/               # Versioned database migrations
│   ├── src/
│   │   └── prooflens/
│   │       ├── __init__.py
│   │       ├── main.py             # FastAPI entrypoint & middleware
│   │       ├── api/
│   │       │   ├── deps.py         # DB session & settings injection
│   │       │   ├── errors.py       # Standard error envelope
│   │       │   └── v1/
│   │       │       ├── router.py
│   │       │       └── routes/     # health, workspaces, documents, search, questions, comparisons, evaluations
│   │       ├── core/
│   │       │   ├── config.py       # Typed Pydantic Settings
│   │       │   ├── logging.py      # Structured logger
│   │       │   ├── security.py     # File validation & path traversal defenses
│   │       │   └── exceptions.py
│   │       ├── domain/
│   │       │   ├── enums.py        # Status codes & relationships
│   │       │   └── policies.py     # Evidence sufficiency & abstention rules
│   │       ├── schemas/            # Pydantic v2 API request/response contracts
│   │       ├── db/
│   │       │   ├── session.py
│   │       │   ├── base.py
│   │       │   └── models/         # SQLAlchemy 2.0 ORM models with pgvector Vector type
│   │       ├── services/           # Business logic: ingestion, chunking, retrieval, answering, citations, comparison
│   │       ├── providers/
│   │       │   ├── llm/            # Base interface + Gemini implementation
│   │       │   └── embeddings/     # Base interface + Gemini implementation
│   │       └── storage/            # Local filesystem storage adapter
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/               # Synthetic/sample PDFs
│   └── scripts/
│       ├── seed_demo.py
│       └── run_evaluation.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── .env.example
│   └── src/
│       ├── app/                    # Next.js App Router (Dashboard, Documents, Ask, Compare, Evaluation)
│       ├── components/             # UI components: Workspace, DocumentList, QuestionForm, CitationViewer, CompareGrid
│       └── lib/                    # API client, TypeScript contracts, formatters
└── var/
    ├── uploads/                    # Local storage for uploaded PDFs (git-ignored)
    └── evaluation-results/         # Run outputs (git-ignored)
```

---

## 4. Phased Milestone Execution Plan

### Milestone 1: Project Skeleton, Environment & Health Checks
**Objective:** Establish local infrastructure, typed configuration, database connection, and baseline FastAPI application with verified health checks.

- **Tasks & Deliverables:**
  1. Create top-level `.gitignore` and `.env.example`.
  2. Create `docker-compose.yml` defining PostgreSQL 16 with `pgvector/pgvector:pg16` image on port 5432 with health check.
  3. Initialize `backend/pyproject.toml` with pinned dependencies (`fastapi`, `uvicorn`, `pydantic-settings`, `sqlalchemy`, `psycopg[binary]`, `pgvector`, `alembic`, `pymupdf`, `google-genai`, `pytest`, `httpx`, `ruff`).
  4. Create `backend/src/prooflens/core/config.py` using `pydantic-settings` to load typed settings.
  5. Create `backend/src/prooflens/core/logging.py` for structured logging.
  6. Create `backend/src/prooflens/db/session.py` with SQLAlchemy engine and sessionmaker.
  7. Initialize Alembic (`alembic.ini`, `alembic/env.py`) and verify baseline connection.
  8. Create FastAPI app in `backend/src/prooflens/main.py` with `/api/v1/health` and `/api/v1/ready` endpoints.
- **Verification Commands:**
  ```bash
  docker compose up -d db
  docker compose ps
  pytest backend/tests/test_health.py
  curl http://localhost:8000/api/v1/health
  curl http://localhost:8000/api/v1/ready
  ```
- **Exit Gate:** Database container healthy, pgvector extension verified via test, and `/api/v1/ready` returns HTTP 200 with `status: "ready"`.

---

### Milestone 2: Document Ingestion & Provenance Pipeline
**Objective:** Enable PDF upload, cryptographic deduplication, local storage, page-aware text extraction with PyMuPDF, and persistent ingestion status tracking.

- **Tasks & Deliverables:**
  1. Alembic migration `001_initial_schema.py`: create tables `workspaces`, `documents`, `document_pages`.
  2. Implement local storage adapter (`backend/src/prooflens/storage/local_filesystem.py`) with path traversal guards.
  3. Implement file validation service (`backend/src/prooflens/core/security.py`) verifying magic bytes (`%PDF`), size caps (max 20MB), and workspace SHA-256 deduplication.
  4. Implement `PyMuPDF` text extraction service (`backend/src/prooflens/services/pdf_extraction.py`) preserving 1-based page numbers and detecting image-only / empty pages.
  5. Implement `workspaces` and `documents` REST API routes (`/api/v1/workspaces`, `/api/v1/workspaces/{id}/documents`).
  6. Unit and integration tests for valid PDFs, duplicate PDFs, corrupt files, and empty page detection.
- **Verification Commands:**
  ```bash
  alembic upgrade head
  pytest backend/tests/unit/test_pdf_extraction.py
  pytest backend/tests/integration/test_document_ingestion.py
  ```
- **Exit Gate:** User can upload a multi-page PDF, obtain page records in the database with strict 1-based page numbers, and query document status via API.

---

### Milestone 3: Page-Aware Chunking, Embeddings & Semantic Retrieval
**Objective:** Split extracted pages into bounded token chunks preserving page metadata, generate 768-dimensional Gemini embeddings, persist them in pgvector, and execute scoped similarity search.

- **Tasks & Deliverables:**
  1. Alembic migration `002_chunks_and_embeddings.py`: create tables `document_chunks` and `chunk_embeddings` with `VECTOR(768)` column and cosine index (`vector_cosine_ops`).
  2. Implement chunking service (`backend/src/prooflens/services/chunking.py`): 700–900 token targets with 100–150 token overlap, preserving document ID, chunk index, and page number array.
  3. Implement `EmbeddingProvider` interface and `GeminiEmbeddingProvider` (`backend/src/prooflens/providers/embeddings/gemini.py`) utilizing `gemini-embedding-2` with `output_dimensionality=768`.
  4. Implement retrieval service (`backend/src/prooflens/services/retrieval.py`): parameterized pgvector cosine query filtering strictly by `workspace_id` and ready `document_ids`.
  5. Implement `/api/v1/workspaces/{id}/search` endpoint.
  6. Unit tests with mocked embeddings and integration tests with real pgvector cosine queries.
- **Verification Commands:**
  ```bash
  alembic upgrade head
  pytest backend/tests/unit/test_chunking.py
  pytest backend/tests/integration/test_retrieval.py
  ```
- **Exit Gate:** Ingested PDF chunks are embedded, stored in pgvector, and a semantic query returns top-k ranked chunks with valid distance scores and source page numbers.

---

### Milestone 4: Grounded Q&A, Citation Validation & Abstention Policy
**Objective:** Build the complete evidence-grounded answering engine with prompt injection defense, server-side citation validation, and deterministic abstention on insufficient evidence.

- **Tasks & Deliverables:**
  1. Alembic migration `003_queries_answers_citations.py`: create tables `query_runs`, `retrieved_evidence`, `answers`, `citations`.
  2. Implement `LLMProvider` interface and `GeminiLLMProvider` (`backend/src/prooflens/providers/llm/gemini.py`) using `gemini-3.8-flash` with structured Pydantic JSON output.
  3. Implement prompt builder with untrusted evidence context delimiters (`<<<EVIDENCE_START>>>`) and anti-injection system prompt.
  4. Implement citation validator (`backend/src/prooflens/services/citation_validation.py`): verify that cited keys (`E1`, `E2`) belong to the retrieved set; resolve document filenames, IDs, and page numbers strictly server-side.
  5. Implement evidence sufficiency policy (`backend/src/prooflens/services/evidence_sufficiency.py`): trigger `insufficient_evidence` when retrieval produces empty/sub-threshold passages or when the model cannot cite supporting evidence.
  6. Implement `/api/v1/workspaces/{id}/questions` endpoint.
  7. Automated tests for grounded Q&A, invalid citation rejection, and forced abstention on out-of-scope questions.
- **Verification Commands:**
  ```bash
  alembic upgrade head
  pytest backend/tests/unit/test_citation_validation.py
  pytest backend/tests/unit/test_evidence_policy.py
  pytest backend/tests/integration/test_question_answering.py
  ```
- **Exit Gate:** Asking an answered question returns text with server-verified page citations; asking an irrelevant or ungrounded question cleanly returns `status: "insufficient_evidence"` with zero hallucinated citations.

---

### Milestone 5: Cross-Document Comparison & Next.js Frontend
**Objective:** Implement multi-document comparison and deliver a premium Next.js web application for workspaces, ingestion status, evidence inspection, and comparison.

- **Tasks & Deliverables:**
  1. Alembic migration `004_comparisons.py`: create tables `comparison_runs`, `comparison_findings`.
  2. Implement comparison service (`backend/src/prooflens/services/comparison.py`): retrieve evidence per selected document (minimum 2), generate structured per-document findings, and classify relationships (`supports`, `differs`, `apparent_contradiction`, `not_comparable`).
  3. Implement `/api/v1/workspaces/{id}/comparisons` endpoint.
  4. Initialize Next.js frontend (`frontend/`): Next.js App Router, TypeScript, Tailwind CSS.
  5. Build UI components & views:
     - **Workspace Dashboard:** create/select workspace.
     - **Document Management:** file dropzone, upload progress bar, status polling (`queued` ➔ `processing` ➔ `ready`).
     - **Ask & Evidence Inspector:** question input, grounded response card, clickable citation badges showing original page excerpts.
     - **Cross-Document Compare:** select 2+ documents, view comparative findings with source badges.
     - **Insufficiency Banners:** clear visual cues when evidence is weak or absent.
  6. Document deletion flow with full cascade cleanup (API + UI).
- **Verification Commands:**
  ```bash
  npm --prefix frontend run build
  npm --prefix frontend run lint
  pytest backend/tests/integration/test_comparison.py
  ```
- **Exit Gate:** User can create a workspace, upload 2 PDFs via browser, ask questions, inspect cited source pages, and run a comparison across both documents in a responsive UI.

---

### Milestone 6: Evaluation Suite, Security Hardening & Demo Readiness
**Objective:** Deliver reproducible evaluation dataset and CLI runner, run prompt-injection security tests, configure demo fixtures, and complete project documentation.

- **Tasks & Deliverables:**
  1. Create curated evaluation dataset (`backend/tests/fixtures/evaluation_cases.jsonl`) with 20+ test cases covering:
     - Document-specific factual questions (expected retrieval & answer).
     - Out-of-scope / absent questions (expected abstention).
     - Cross-document comparison queries.
  2. Implement evaluation CLI runner (`backend/scripts/run_evaluation.py`) computing:
     - Retrieval Hit Rate
     - Citation Validity Rate
     - Abstention Accuracy
  3. Implement prompt injection adversarial tests (`backend/tests/security/test_prompt_injection.py`) ensuring PDFs containing malicious overrides do not compromise the system prompt.
  4. Create demo seeder script (`backend/scripts/seed_demo.py`) that provisions a demonstration workspace with sample academic/technical PDF reports.
  5. Finalize root `README.md` with step-by-step setup instructions for local development and demonstration.
- **Verification Commands:**
  ```bash
  python backend/scripts/run_evaluation.py
  pytest backend/tests/security/test_prompt_injection.py
  python backend/scripts/seed_demo.py
  ```
- **Exit Gate:** Evaluation script runs reproducibly reporting >80% retrieval hit rate, 100% citation validity, and >85% abstention accuracy. Complete setup documented and verified from clean clone.

---

## 5. Review Gates & Acceptance Criteria Summary

| Milestone | Gate Criteria | Approver |
|---|---|---|
| **M1: Skeleton & DB** | Dockerized PostgreSQL+pgvector healthy, `/api/v1/ready` returns 200, Alembic runs cleanly. | Owner |
| **M2: Ingestion & Extraction** | PDF upload succeeds, SHA-256 deduplication works, page text extracted with 1-based page indices. | Owner |
| **M3: Chunking & Retrieval** | Chunks generated with page arrays, 768-dim embeddings stored, pgvector similarity query returns relevant chunks. | Owner |
| **M4: Grounded Q&A** | Answers cite only real passages; server rejects invalid citation references; abstains on missing evidence. | Owner |
| **M5: Comparison & UI** | Full Next.js frontend operational; comparison highlights differences; source inspection works smoothly. | Owner |
| **M6: Evaluation & Demo** | CLI evaluation runs with documented metrics; prompt-injection tests pass; demo script ready for presentation. | Owner |

---

## 6. Next Steps

Upon review and decision confirmation by the owner:
1. Confirm Technical Decisions (**D1** through **D5**).
2. Begin **Milestone 1**: Initialize `docker-compose.yml`, backend dependencies, FastAPI app factory, configuration, and health check tests.
