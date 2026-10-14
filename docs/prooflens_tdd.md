# ProofLens AI — Technical Design Document (TDD) and Software Requirements Specification (SRS)

**Document ID:** PLAI-TDD-001  
**Version:** 0.1  
**Status:** Draft for owner review — architecture proposal, not implementation approval  
**Product:** ProofLens AI — From Documents to Verifiable Answers  
**Source baseline:** ProofLens AI — Project Kickoff Brief & Initial Product Requirements Document (PRD), PLAI-PRD-001, v0.1  
**Implementation status:** No application code is specified or created by this document.

---

## 1. Purpose and Document Status

This document translates the ProofLens AI kickoff PRD and the confirmed ten-step project workflow into a concrete technical design and SRS for a new, initially empty project folder. It is intended to be reviewed and finalized before the separate implementation plan is written.

It defines the proposed architecture, module boundaries, functional and non-functional requirements, data model, API contracts, ingestion and retrieval workflow, evidence policy, security controls, testing approach, local development setup, and technical decisions.

This is a design proposal, not evidence that any component has already been implemented or tested. Where the PRD leaves decisions open, this document recommends conservative defaults and labels them as proposed decisions. Owner approval is required for decisions that materially affect cost, privacy, architecture, or scope.

### 1.1 Source-of-truth rules

1. The PRD is the product-scope baseline.
2. The confirmed workflow in Section 6 is the required end-to-end processing model.
3. This TDD makes technical recommendations needed to implement that scope; recommendations are not silently treated as already approved.
4. The later `docs/IMPLEMENTATION-PLAN.md` should sequence the work defined here. It must not quietly broaden the MVP.
5. If an implementation repository or governing `AGENTS.md` is present when implementation begins, inspect it first and reconcile this design with the actual repository before editing.

## 2. Product Overview

ProofLens AI is an evidence-first document intelligence web application. Users create a workspace, upload multiple supported PDFs, ask questions across the selected collection, inspect source passages and page-level citations, compare findings across documents, and run a repeatable evaluation set.

The system's central promise is traceability—not guaranteed truth. A citation can be syntactically valid and still fail to justify a claim. Citation-reference validation, evidence sufficiency, and factual correctness are distinct concerns.

### 2.1 Goals

- Ingest supported PDFs and preserve page-level provenance.
- Retrieve semantically relevant passages from a workspace or selected document scope.
- Produce answers grounded in retrieved passages and expose the supporting evidence.
- Abstain or state limitations when evidence is missing, weak, or conflicting.
- Compare findings across at least two documents without manufacturing agreement or contradiction.
- Provide a small, repeatable evaluation suite for retrieval, citations, and abstention.
- Keep provider-specific integrations replaceable and the core pipeline testable.

### 2.2 MVP non-goals

- Autonomous agents, multi-agent orchestration, LangGraph, or MCP.
- Fine-tuning or training a foundation model.
- Guaranteed truth detection or infallible verification.
- Unrestricted web research or internet browsing as part of answering.
- OCR for every scanned PDF in the first release, unless separately approved.
- Enterprise SSO, billing, or complex multi-tenant commercial features.
- Universal document-format or language support.
- Replacing human review in high-stakes decisions.

## 3. Scope and Assumptions

### 3.1 MVP scope

- Next.js browser application.
- Python + FastAPI API.
- PostgreSQL with pgvector.
- PDF upload, validation, page-aware text extraction, chunking, embeddings, and indexing.
- Workspace-scoped semantic retrieval.
- Evidence-grounded question answering with server-validated citations.
- Explicit insufficient-evidence outcomes.
- Source passage inspection.
- Cross-document comparison.
- Curated evaluation cases and a reproducible evaluation command.
- Local development with Docker Compose.
- Automated tests, safe logging, documented configuration, and deletion behaviour.

### 3.2 Proposed defaults for open decisions

| Decision | Proposed MVP default | Reason / approval note |
|---|---|---|
| LLM provider | Google Gemini API through the official `google-genai` Python SDK; initial model `gemini-3.8-flash` | Owner-selected provider. Keep the internal adapter replaceable; verify current model availability, pricing, limits, and structured-output support during implementation. |
| Embedding provider/model | Google Gemini API; initial model `gemini-embedding-2`, `EMBEDDING_DIMENSION=768` | Owner-selected provider/model. Use the same model and dimension for document chunks and query embeddings; evaluate retrieval quality before locking the first migration. |
| API contract | REST JSON under `/api/v1` | Simple, inspectable, and suitable for FastAPI + Next.js. |
| Authentication | Single-user/local-demo mode initially, with an explicit deployment warning; do not imply secure multi-user isolation without authorization | The PRD leaves authentication open. Add server-side auth before exposing the app to multiple users or the public internet. |
| Workspace ownership | Every document and query is scoped to a workspace; add `owner_id` when authentication is introduced | Keeps data boundaries explicit from the start. |
| PDF parser | `pymupdf` for page-level text extraction | Good page-aware extraction; scanned/image-only pages may yield no usable text. Validate library licensing and project requirements before adoption. |
| Chunking | Page-aware, configurable token-based chunks with overlap; do not merge page provenance invisibly | Keeps citations inspectable and makes chunking tunable. |
| Background processing | Synchronous orchestration for the first small demo only if strict file/page limits keep requests bounded; expose status and use a background task/worker boundary | The PRD says not to add a queue unless justified. If uploads take too long or need durability, introduce a worker in a later approved phase. FastAPI in-process background tasks are not durable across restarts. |
| Uploaded file storage | Local filesystem behind a storage interface for development | Object storage is deferred until deployment needs are known. |
| DB migrations | Alembic | Standard explicit migration history for SQLAlchemy-based projects. |
| ORM/database access | SQLAlchemy 2.x with psycopg 3; use parameterized ORM/query APIs | Mature PostgreSQL support and typed boundaries. Raw SQL is acceptable for pgvector-specific queries if parameterized. |
| API schemas | Pydantic v2 models | Native FastAPI integration and explicit validation. |
| Evaluation | Version-controlled JSONL test cases plus a documented Python CLI | Repeatable and easy to review; model-judged scores must be labeled as model-based. |
| Frontend styling | Tailwind CSS with accessible component primitives; exact component library is an implementation choice | Keeps UI consistent without committing to an unnecessary design system. |
| Package management | `uv` for Python; npm (or pnpm if the owner selects it) for Next.js | Choose one lockfile-backed tool per runtime and document it. Do not mix package managers. |
| API docs | FastAPI-generated OpenAPI at `/docs` in development | Makes request/response contracts inspectable. Disable or restrict interactive docs in production if appropriate. |

**Approval gate:** Gemini is selected for both external APIs. Before coding, confirm model availability/pricing and the proposed 768-dimensional embedding configuration, along with authentication/demo mode, maximum PDF size/page count, and whether processing must survive server restarts. Safe defaults can be used for other choices unless the owner objects.

## 4. System Architecture

### 4.1 Logical architecture

```text
Browser
  |
  v
Next.js frontend
  |  REST/JSON (/api/v1)
  v
FastAPI application
  |-- Workspace and document API
  |-- Ingestion orchestration
  |    |-- File validation/storage
  |    |-- PDF page extraction
  |    |-- Page-aware chunking
  |    |-- Embedding provider adapter
  |    `-- Persistence/status updates
  |-- Retrieval service
  |    `-- PostgreSQL + pgvector similarity search
  |-- RAG answer service
  |    |-- Evidence sufficiency policy
  |    |-- LLM provider adapter
  |    `-- Citation reference validation
  |-- Comparison service
  `-- Evaluation service
       |
       +--> External embedding API
       +--> External LLM API
       `--> PostgreSQL + pgvector

Local file storage (behind a storage interface) holds original PDFs.
```

### 4.2 Component responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| Next.js UI | Workspace/document views, upload progress/status, question input, answer/evidence display, comparison, evaluation summary | Call LLM/embedding providers directly or expose provider secrets |
| FastAPI routers | HTTP validation, authentication/authorization boundary, status codes, request/response serialization | Contain full RAG or parsing algorithms |
| Application services | Coordinate use cases and transactions | Depend directly on UI code |
| PDF extraction adapter | Extract page text and extraction metadata | Invent text for image-only pages |
| Chunking service | Create bounded chunks and preserve document/page/chunk provenance | Drop provenance or silently cross page boundaries without recording all pages |
| Embedding adapter | Call selected embedding API, enforce dimensions and bounded retries | Store API keys in database or return them to clients |
| Retrieval service | Apply workspace/document filters, vector distance and result limits | Search outside the requested scope |
| Answer service | Build evidence context, request a structured grounded answer, apply insufficiency policy | Treat model confidence or fluent wording as proof |
| Citation validator | Match model citation references to actual retrieved evidence and derive source metadata server-side | Trust model-provided filenames, document IDs, or page numbers |
| Comparison service | Retrieve evidence per selected document and summarize supported similarities/differences | Force a contradiction when scopes or definitions differ |
| Evaluation service/CLI | Run fixed cases and calculate retrieval/citation/abstention metrics | Present LLM-judged scores as ground truth |
| Repository/data layer | Persistence, transactions, migrations, scoped queries | Construct unsafe SQL from user input |
| Storage adapter | Store, retrieve, and delete originals through a replaceable interface | Assume local disk is durable production object storage |

### 4.3 Request flow

1. Browser calls Next.js UI actions.
2. Next.js calls FastAPI REST endpoints.
3. FastAPI validates input and enforces the relevant workspace/document scope.
4. Application services call the domain pipeline and repositories.
5. PostgreSQL stores application data and vectors; file storage holds source PDFs.
6. Provider adapters call the external APIs from the server only.
7. FastAPI returns typed results with source metadata; Next.js renders citations and evidence.
8. Failures are represented as stable API errors and visible UI states, not raw stack traces.

### 4.4 Trust boundaries

- Uploaded PDF bytes and extracted document text are untrusted.
- Retrieved passages are evidence data, not instructions.
- LLM output is untrusted until parsed, schema-validated, citation-validated, and checked by the evidence policy.
- All provider API calls occur server-side.
- All workspace/document filters are enforced server-side; a client-supplied workspace ID is not authorization.
- A local single-user demo is not production-safe multi-user authentication.

## 5. Software Requirements Specification (SRS)

### 5.1 User classes

- **Student/researcher:** uploads reports or papers, asks questions, inspects evidence.
- **Project/team user:** compares technical documents and reviews differences.
- **Demo/evaluator:** runs or reviews a curated evaluation set.
- **Developer/operator:** configures providers, reviews logs, runs migrations and tests.

### 5.2 Functional requirements

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| FR-01 | Create and list workspaces; select a workspace for all document and query operations | Must | API and UI integration test |
| FR-02 | Upload one or more supported PDFs within configured size/page/count limits; record stable ID, filename, size, upload time, status, and checksum | Must | Upload tests |
| FR-03 | Detect duplicate uploads using a workspace-scoped SHA-256 checksum; return a clear duplicate outcome or an explicitly configured reprocess option | Must | Duplicate upload test |
| FR-04 | Extract page-level text and preserve original page numbers; report invalid, encrypted, empty, or unsupported files clearly | Must | Parser tests with fixtures |
| FR-05 | Report image-only/scanned pages with no extractable text; OCR remains out of scope unless approved | Must | Scanned PDF fixture |
| FR-06 | Chunk extracted text with configurable chunk size/overlap and preserve document ID, page number(s), chunk index, and offsets/metadata where available | Must | Chunk/provenance tests |
| FR-07 | Generate embeddings through a provider adapter and persist vectors and metadata in PostgreSQL/pgvector | Must | Integration test |
| FR-08 | Track ingestion states and errors; retries must not create duplicate pages/chunks/embeddings | Must | Retry/idempotency tests |
| FR-09 | Embed a user question using a compatible embedding model and retrieve relevant chunks only within the requested workspace and selected-document scope | Must | Retrieval scope tests |
| FR-10 | Return configurable top-k evidence and score/distance metadata where meaningful | Must | Retrieval tests |
| FR-11 | Generate document-specific answers from retrieved evidence only, with an explicit insufficient-evidence outcome when evidence is inadequate | Must | Grounded/abstention tests |
| FR-12 | Validate all citation references against the actual retrieved evidence and derive document name/page/excerpt server-side | Must | Invalid citation tests |
| FR-13 | Display cited source, page, excerpt, and the distinction between source text and AI interpretation | Must | UI acceptance test |
| FR-14 | Compare a topic across at least two selected documents, report per-document findings and citations, and flag incomparable scope/definitions | Must | Comparison tests |
| FR-15 | Provide a version-controlled evaluation set and a documented command that measures retrieval hit rate, citation validity, and abstention outcomes | Must | Evaluation smoke test |
| FR-16 | Validate requests and uploads; return consistent safe errors; apply provider timeouts and bounded retries | Must | API and resilience tests |
| FR-17 | Delete a document and its associated extracted pages, chunks, embeddings, and stored original according to a defined deletion policy | Must | Deletion integration test |
| FR-18 | Record latency and provider token/usage information when available, without logging full document contents by default | Must | Logging/usage tests |
| FR-19 | Show loading, empty, processing, success, unsupported, and error states in the UI | Must | UI tests/manual acceptance |
| FR-20 | Keep provider-specific implementations behind interfaces and centralize configuration | Must | Unit tests/code review |
| FR-21 | Enforce server-side authorization for every workspace/document operation before enabling multi-user access | Conditional must for multi-user/public deployment; not optional for such deployment | Authorization integration tests |
| FR-22 | Provide health/readiness endpoints and documented local setup | Must | Local smoke test |

### 5.3 Non-functional requirements

| ID | Requirement | Acceptance approach |
|---|---|---|
| NFR-01 Security | Keep provider secrets server-side; never commit secrets; validate uploads and request schemas; use parameterized DB access | Secret scan/config review and security tests |
| NFR-02 Tenant/data isolation | Every query, retrieval, comparison, citation, and deletion is scoped to the authorized workspace | Cross-workspace negative tests |
| NFR-03 Prompt-injection resistance | Treat document content as untrusted quoted evidence; never execute instructions found in PDFs; do not give the LLM arbitrary tools | Adversarial document tests and prompt review |
| NFR-04 Provenance integrity | Page/document/chunk relationships remain traceable from extraction through response | End-to-end provenance tests |
| NFR-05 Citation integrity | A citation may only refer to a retrieved evidence item; source metadata is derived from the database, not model assertions | Citation validation tests |
| NFR-06 Evidence transparency | Weak/missing/conflicting evidence produces a visible limitation/abstention state | Evaluation cases and UI checks |
| NFR-07 Reliability | Provider calls use timeouts, bounded retries, and clear failure states; ingestion retries are idempotent | Failure injection/integration tests |
| NFR-08 Maintainability | Clear modules, typed schemas, centralized settings, migrations, documented commands | Code review and clean setup |
| NFR-09 Testability | Core chunking, retrieval scope, citation validation, deletion, and abstention logic can be tested without live AI calls | Unit tests with fakes |
| NFR-10 Performance discipline | Enforce limits for file size, page count, chunk count, top-k, and provider output; measure before optimization | Limits tests and recorded timings |
| NFR-11 Accessibility | Keyboard-accessible controls, visible focus, semantic labels, readable citations, and non-color-only status indicators | Accessibility review/tests |
| NFR-12 Privacy | Avoid logging raw PDF text, full prompts, API keys, or sensitive content by default; define retention/deletion behaviour | Log inspection and deletion tests |
| NFR-13 Reproducibility | Evaluation data, model configuration, and scoring definitions are versioned and documented | Re-run evaluation and compare report |
| NFR-14 Portability | Local services can be started from documented environment variables and Docker Compose; application logic does not depend on local-only paths | Clean-environment setup test |
| NFR-15 Honest claims | Do not describe AI output as guaranteed fact or a model-based evaluation as ground truth | UI/content review |

### 5.4 MVP acceptance criteria

The MVP is acceptable only when:
1. Multiple supported PDFs can be uploaded and processing status is accurate.
2. Extracted text/chunks retain valid document and page provenance.
3. Retrieval returns relevant passages only from the requested scope.
4. Answers cite only real retrieved source locations.
5. Unsupported questions produce an explicit insufficient-evidence result.
6. Users can inspect each citation's source excerpt.
7. Comparison shows evidence per document and avoids unsupported contradiction claims.
8. Automated tests cover ingestion, retrieval, citations, abstention, scoping, and deletion.
9. The curated evaluation command runs reproducibly and explains metric limitations.
10. Another developer can start the project using the documented setup.
11. Secrets are not committed or exposed to the browser.
12. A prepared sample document set supports an end-to-end demonstration.

## 6. Authoritative End-to-End Workflow

The following is the required core workflow. It is split into ingestion and question answering, and must remain traceable through the API, database, tests, and UI.

### Phase A — Document ingestion (steps 1–5)

#### Step 1: Upload PDF
- Client submits a PDF to the workspace upload endpoint.
- Backend validates extension, MIME hint, file signature, size, and configured limits. MIME/extension alone is not sufficient validation.
- Backend calculates SHA-256, creates a stable `document_id`, stores the original through the storage abstraction, and records filename, size, checksum, upload timestamp, and status.
- Status begins at `queued` or `processing`, then progresses through extraction/indexing to `ready` or `failed`.
- Duplicate policy is workspace-scoped and deterministic.

#### Step 2: Extract text from PDF
- Parser processes each page separately.
- Persist extracted page text with a 1-based source page number and extraction metadata.
- Invalid, encrypted, empty, or unsupported PDFs fail with a safe, actionable error code.
- Pages with no extractable text are recorded/flagged. OCR is not silently invoked in the MVP.

#### Step 3: Chunk extracted text
- Split text into bounded, configurable chunks; use a token-aware strategy if the selected tokenizer is available.
- Recommended starting configuration: 700–900 tokens per chunk with 100–150 token overlap, to be tuned by evaluation rather than treated as a performance guarantee.
- Prefer chunks contained within a single page for simple, precise citations. If a chunk spans pages, store the complete page-number set and character/token boundaries; never assign an arbitrary single page.
- Each chunk carries `document_id`, `page_number` or `page_numbers`, `chunk_index`, text, and metadata.

#### Step 4: Generate embeddings for chunks
- Batch chunks according to provider limits.
- Use a configured embedding model and record provider/model/version metadata.
- Validate vector dimension and batch response cardinality.
- Retry transient provider failures a bounded number of times with backoff; do not retry permanent invalid-input failures indefinitely.
- If embedding fails, mark ingestion failed or retryable without duplicating already committed chunks.

#### Step 5: Store chunks, embeddings, and metadata in PostgreSQL + pgvector
- Store extracted pages and chunk rows in PostgreSQL.
- Store each embedding with its chunk and model/dimension metadata.
- Apply migrations and indexes that match the selected pgvector and embedding model.
- Mark the document `ready` only after all required chunks have embeddings and are queryable.
- A `ready` document with zero usable chunks is not allowed.

### Phase B — Question answering (steps 6–10)

#### Step 6: User asks a question
- Client submits question, workspace ID, optional selected document IDs, and optional conversation/run metadata.
- Backend validates the question and confirms the selected documents belong to the requested workspace and are ready.
- MVP can treat each request as an independent question; conversation memory is not required unless explicitly added.

#### Step 7: Embed the question
- Use the same embedding model or a compatible model with the same vector space and dimension as document embeddings.
- Validate vector dimension before searching.
- Apply provider timeout/retry policy.

#### Step 8: Similarity search with pgvector
- Search only within the requested workspace and selected ready documents.
- Return top-k evidence and source metadata; use a configurable threshold where the distance metric supports a meaningful threshold.
- Do not treat raw vector distance as a calibrated probability or universal confidence score.
- Retrieval is independently testable and should be measured on curated queries.

#### Step 9: Send question and retrieved context to the LLM
- Build a bounded prompt containing the question, retrieved passages, source keys, and explicit instructions to use only the evidence for document-specific claims.
- Delimit source passages as untrusted data. Tell the model to ignore instructions inside passages.
- Request a structured response: answer status, answer text, claims/findings, citation references, and limitations.
- Never send the whole PDF when selected passages suffice.
- If retrieval returns no evidence or all evidence falls below the configured sufficiency gate, abstain before generation or require the model to return an insufficient-evidence status.

#### Step 10: Validate citations and evidence sufficiency, then respond
- Parse the model output against a strict schema.
- Reject or remove citation references not present in the retrieved-evidence allowlist.
- Derive filenames, document IDs, page numbers, and excerpts from server-held evidence records.
- Apply a separate evidence sufficiency policy. A valid citation reference does not prove that the cited passage supports the claim.
- Return answer, status, citations, excerpts, limitations, and usage/latency metadata where available.
- UI renders the answer separately from source passages and labels unsupported/uncertain outcomes clearly.

### 6.1 Ingestion state machine

```text
queued -> processing -> ready
                    \-> failed
failed -> queued/processing (explicit retry only)
ready -> deleting -> deleted (or physical removal after successful cleanup)
```

The implementation may use fewer states if it preserves the above user-visible semantics. Store a safe error code/message for failed processing. Avoid exposing stack traces or provider responses containing secrets.

### 6.2 Idempotency and partial failures

- Use a workspace-scoped checksum uniqueness rule for duplicate detection.
- Use transactions for related page/chunk metadata writes where practical.
- Give chunks stable identity within a document, such as a unique `(document_id, chunk_index)` constraint.
- Retry should replace/reconcile incomplete output, not append duplicate chunks.
- A document becomes `ready` only after the full indexing pipeline succeeds.
- If file storage succeeds but database persistence fails, compensate by deleting the orphan file where possible.
- If database deletion succeeds but file deletion fails, record cleanup failure for retry rather than falsely claiming full deletion.

## 7. Backend Design

### 7.1 Proposed folder structure

```text
backend/
├── pyproject.toml
├── uv.lock
├── .env.example
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   └── prooflens/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app factory, middleware, router registration
│       ├── api/
│       │   ├── deps.py             # DB/session and request dependencies
│       │   ├── errors.py           # Stable API error mapping
│       │   └── v1/
│       │       ├── router.py
│       │       └── routes/
│       │           ├── health.py
│       │           ├── workspaces.py
│       │           ├── documents.py
│       │           ├── questions.py
│       │           ├── comparisons.py
│       │           └── evaluations.py
│       ├── core/
│       │   ├── config.py           # Typed environment configuration
│       │   ├── logging.py
│       │   ├── security.py         # Auth/authorization boundary and file checks
│       │   └── exceptions.py
│       ├── db/
│       │   ├── base.py
│       │   ├── session.py
│       │   ├── models/
│       │   └── repositories/
│       ├── schemas/                # Pydantic API request/response models
│       ├── domain/
│       │   ├── enums.py
│       │   └── policies.py         # Evidence/abstention policy definitions
│       ├── services/
│       │   ├── workspaces.py
│       │   ├── documents.py
│       │   ├── ingestion.py
│       │   ├── pdf_extraction.py
│       │   ├── chunking.py
│       │   ├── embeddings.py
│       │   ├── retrieval.py
│       │   ├── answering.py
│       │   ├── citation_validation.py
│       │   ├── evidence_sufficiency.py
│       │   ├── comparison.py
│       │   └── evaluation.py
│       ├── providers/
│       │   ├── llm/
│       │   │   ├── base.py
│       │   │   └── selected_provider.py
│       │   └── embeddings/
│       │       ├── base.py
│       │       └── selected_provider.py
│       └── storage/
│           ├── base.py
│           └── local_filesystem.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── fixtures/
│   └── evaluation/
└── scripts/
    ├── seed_demo.py
    └── run_evaluation.py
```

This is a proposed boundary map, not a requirement to create empty modules mechanically. Start with the smallest modules needed for the first vertical slice; keep the named responsibilities separate as complexity grows.

### 7.2 Module boundaries

- `api/`: HTTP-only concerns, dependency injection, request validation, status codes, and response schemas.
- `schemas/`: external request/response contracts. Do not return ORM objects directly.
- `services/`: use-case orchestration and business rules.
- `domain/`: enums and policies that should not depend on FastAPI or a specific provider.
- `db/models/`: relational mappings and pgvector column definitions.
- `db/repositories/`: scoped persistence and query logic.
- `providers/`: replaceable LLM/embedding adapters; no business policy.
- `storage/`: original-file storage contract and implementation.
- `tests/`: unit tests use fakes; integration tests use a real test PostgreSQL/pgvector instance where needed.
- `scripts/`: reproducible developer/evaluation commands, not production API logic.

### 7.2.1 Selected AI provider integration: Google Gemini

Google Gemini is the selected external provider for both AI capabilities in the MVP:

- **Answer generation:** Gemini API model `gemini-3.8-flash` (initial proposed model ID).
- **Embeddings:** Gemini API model `gemini-embedding-2` (initial proposed model ID), using `output_dimensionality=768` as the initial database configuration.
- **SDK:** `google-genai` in the Python backend. Calls must remain server-side; the Next.js browser must never call Gemini directly or receive the API key.
- **Credential:** one backend-only `GEMINI_API_KEY` is shared by the generation and embedding adapters. Do not create duplicate secret variables for the same credential.
- **Abstraction:** implement separate internal `LLMProvider` and `EmbeddingProvider` interfaces with Gemini-backed adapters. Keep evidence policy, citation validation, retrieval orchestration, and application schemas independent of the vendor SDK. Do not add a second provider unless explicitly approved.
- **Embedding consistency:** use the exact same embedding model, task/prompt conventions, and configured output dimension for document chunks and user questions. Persist provider/model/version/dimension metadata. Do not compare vectors from incompatible embedding models. A model or embedding-space change requires a planned re-embedding operation and potentially a migration.
- **Failure handling:** configure bounded timeouts and retries for transient errors; handle quota/rate-limit, authentication, invalid-input, and provider-unavailable responses with safe user-facing errors. Do not log API keys, raw provider payloads, or full document contents by default.
- **Privacy and cost:** document that selected PDF text chunks and user questions are sent to Google's API for embedding/generation. Review current Google API terms, data handling, quotas, and pricing before using sensitive documents or deploying publicly. Apply chunk/context/output limits and track usage where returned by the API.
- **Model verification gate:** before locking dependencies or migrations, verify that the selected model IDs are available to the project/API key and that the chosen generation configuration and 768-dimensional embeddings work end-to-end. Run a curated retrieval and grounded-answer evaluation; model names are configuration, not guarantees of quality or permanence.

Official references: https://ai.google.dev/gemini-api/docs/text-generation and https://ai.google.dev/gemini-api/docs/embeddings.

### 7.3 Proposed dependencies and tools

Pin compatible versions in lockfiles at implementation time. The following is a recommended dependency set, not a claim that these packages are installed.

**Backend runtime**
- `fastapi` — API framework.
- `uvicorn[standard]` — ASGI server.
- `pydantic` and `pydantic-settings` — validation and environment configuration.
- `sqlalchemy` 2.x — relational ORM and transactions.
- `psycopg[binary]` or an approved psycopg 3 distribution — PostgreSQL driver; choose one deployment strategy and document it.
- `pgvector` Python integration — vector type and distance operations.
- `alembic` — database migrations.
- `pymupdf` — page-aware PDF text extraction, subject to licensing/approval.
- `google-genai` — official Google Gen AI SDK for both Gemini text generation and embedding calls, behind internal provider interfaces.
- `httpx` — provider HTTP integration if not fully handled by the SDK and for API tests.
- `tenacity` or a small internal retry utility — bounded retries only; avoid stacked retry layers.
- `python-multipart` — multipart upload parsing.
- `structlog` or standard-library structured logging — select one approach.
- `orjson` is optional; do not add without measured benefit.

**Backend development/test tools**
- `pytest`, `pytest-cov`, `pytest-asyncio` if async tests require it.
- `ruff` — linting/formatting.
- `mypy` or `pyright` — choose one type checker.
- `httpx` — FastAPI test client support.
- Optional `testcontainers` only if it materially simplifies disposable PostgreSQL integration tests; Docker Compose can be sufficient.

**Frontend runtime**
- `next` — Next.js App Router.
- `react`, `react-dom`.
- `typescript`.
- `zod` — runtime validation of client-side forms/API payloads where useful.
- `react-hook-form` — optional form state management; use only if forms warrant it.
- `tailwindcss` and the required Next.js/PostCSS integration — styling.
- A small accessible component primitive library may be selected after UI needs are known; do not add multiple overlapping UI libraries.
- `lucide-react` — optional consistent icons.

**Frontend development/test tools**
- ESLint with the Next.js configuration.
- Prettier if selected consistently across the repository.
- `vitest` and React Testing Library for component/unit tests, or the repository's chosen compatible test stack.
- `playwright` for a small set of end-to-end critical-path tests.
- `axe-core`/Playwright accessibility checks are optional but useful.

**Infrastructure/tooling**
- Docker and Docker Compose for local PostgreSQL/pgvector and repeatable development.
- PostgreSQL version and pgvector extension version must be selected and tested together.
- `.env.example` with placeholder values only.
- Git ignore rules for `.env`, local PDFs, generated evaluation outputs, caches, and secrets.
- No Redis, Celery, Kafka, Kubernetes, LangChain, LangGraph, MCP, or agent framework in the initial design.

## 8. Frontend Design

### 8.1 Proposed folder structure

```text
frontend/
├── package.json
├── package-lock.json
├── next.config.ts
├── tsconfig.json
├── .env.example
├── public/
│   └── (static assets only)
└── src/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx                     # Workspace landing/dashboard
    │   ├── workspaces/
    │   │   ├── page.tsx                 # Workspace list/create
    │   │   └── [workspaceId]/
    │   │       ├── page.tsx             # Workspace overview/document library
    │   │       ├── documents/
    │   │       │   └── [documentId]/page.tsx  # Document status/details
    │   │       ├── ask/page.tsx          # Question answering/evidence
    │   │       ├── compare/page.tsx      # Cross-document comparison
    │   │       └── evaluation/page.tsx   # Evaluation summary
    │   ├── error.tsx
    │   ├── loading.tsx
    │   └── not-found.tsx
    ├── components/
    │   ├── layout/
    │   ├── workspaces/
    │   ├── documents/
    │   ├── upload/
    │   ├── questions/
    │   ├── evidence/
    │   ├── comparison/
    │   ├── evaluation/
    │   ├── feedback/
    │   └── ui/
    ├── lib/
    │   ├── api-client.ts                # Typed fetch wrapper and safe error parsing
    │   ├── api-types.ts                 # Types aligned with API contract
    │   ├── validators.ts                # Zod schemas, if needed
    │   └── formatters.ts
├── tests/
│   ├── components/
│   └── e2e/
└── (configuration files)
```

Use the App Router. Keep server components as the default where possible; use client components only for interactive forms, upload progress, question entry, tabs, and source inspection. Never place provider secrets in `NEXT_PUBLIC_*` variables.

### 8.2 Pages and component responsibilities

- **Workspace landing/list:** create/select workspace; show recent workspaces if available.
- **Workspace overview:** list documents, upload files, show status and safe error messages, filter/select documents.
- **Document details:** show filename, upload time, processing state, page/chunk counts when available, and delete/retry controls.
- **Ask page:** question form, selected document scope, answer state, insufficiency banner, citations and source excerpts.
- **Evidence viewer:** display document name, page number, excerpt, and whether the text is quoted source or AI interpretation. A PDF viewer is optional; the MVP can show stored source excerpts without building a full PDF annotation viewer.
- **Comparison page:** require at least two ready documents, accept a topic/question, display per-document findings, citations, and scope/definition caveats.
- **Evaluation page:** show last evaluation summary or trigger a run only if the API's operational policy allows it; evaluation execution may remain a developer CLI in the MVP.
- **Global feedback states:** loading, empty, unsupported file, insufficient evidence, API/provider failure, and retry guidance.

### 8.3 Frontend/API rules

- All API base URLs come from a server-side or explicitly configured public API URL appropriate to deployment.
- Use typed request/response shapes matching Section 10.
- Render API errors as user-safe messages; never display stack traces or raw provider payloads.
- Disable duplicate submissions while an operation is pending.
- Use accessible labels, keyboard navigation, visible focus, and semantic status text.
- Poll document status at a bounded interval only while documents are processing; stop polling on terminal state.
- If authentication is added, do not treat a hidden UI control as an authorization mechanism.

## 9. Database Design

### 9.1 PostgreSQL and pgvector decisions

- PostgreSQL stores relational application data, extracted page text, chunks, retrieval/query records, and evaluation metadata.
- pgvector stores chunk embeddings and supports similarity search.
- Enable the `vector` extension through a versioned migration.
- The vector column dimension must equal the configured Gemini embedding model's output dimension. The initial proposed model is `gemini-embedding-2` with `output_dimensionality=768`; verify the configured dimension against the actual API response and lock it before the first vector migration.
- Do not switch embedding models with different dimensions without a planned re-embedding/migration strategy.
- Use a vector index only after verifying compatibility with the selected pgvector version, distance metric, data size, and filtering strategy. For a small demo, exact search may be adequate; measure before adding index complexity.
- Prefer cosine distance as the initial similarity metric unless the chosen model/provider documentation recommends otherwise. A distance score is not a probability.
- Apply workspace/document filtering in the SQL query, not after results return to the application.

### 9.2 Entity relationship overview

```text
Workspace 1 ─── N Document
Document  1 ─── N DocumentPage
Document  1 ─── N DocumentChunk
DocumentChunk 1 ─── 0..1 ChunkEmbedding (or embedding columns on chunk)
Workspace 1 ─── N QueryRun
QueryRun  1 ─── N RetrievedEvidence
QueryRun  1 ─── 0..1 Answer
Answer    1 ─── N Citation
Workspace 1 ─── N ComparisonRun
ComparisonRun 1 ─── N ComparisonFinding
EvaluationCase 1 ─── N EvaluationResult
EvaluationRun 1 ─── N EvaluationResult
```

The logical model separates chunk content from embeddings so model version/dimension can be recorded and future re-embedding can be managed. If the MVP uses exactly one embedding model and only one vector per chunk, embedding columns can be placed directly on `document_chunks` for simplicity; choose one representation and keep it consistent. This design recommends a separate `chunk_embeddings` table for clearer model lifecycle management.

### 9.3 Proposed tables

#### `workspaces`
- `id UUID PRIMARY KEY`
- `name VARCHAR(160) NOT NULL`
- `description TEXT NULL`
- `owner_id UUID NULL` — reserved for future/auth-enabled deployment; do not infer authorization from NULL
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

Indexes: primary key; optional index on `created_at`.

#### `documents`
- `id UUID PRIMARY KEY`
- `workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
- `original_filename VARCHAR(255) NOT NULL`
- `content_type VARCHAR(100) NOT NULL`
- `size_bytes BIGINT NOT NULL CHECK (size_bytes > 0)`
- `sha256 CHAR(64) NOT NULL`
- `storage_key TEXT NOT NULL`
- `status VARCHAR(24) NOT NULL CHECK (status IN ('queued','processing','ready','failed','deleting','deleted'))`
- `page_count INTEGER NULL CHECK (page_count IS NULL OR page_count >= 0)`
- `chunk_count INTEGER NULL CHECK (chunk_count IS NULL OR chunk_count >= 0)`
- `error_code VARCHAR(80) NULL`
- `error_message TEXT NULL` — sanitized user-safe message only
- `uploaded_at TIMESTAMPTZ NOT NULL`
- `processing_started_at TIMESTAMPTZ NULL`
- `processed_at TIMESTAMPTZ NULL`
- `deleted_at TIMESTAMPTZ NULL`

Constraints/indexes:
- `UNIQUE (workspace_id, sha256)` for duplicate prevention, unless approved re-upload semantics require versioning.
- Index `(workspace_id, status, uploaded_at DESC)`.
- Never expose `storage_key` as a public URL.

#### `document_pages`
- `id UUID PRIMARY KEY`
- `document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE`
- `page_number INTEGER NOT NULL CHECK (page_number >= 1)`
- `text_content TEXT NOT NULL`
- `character_count INTEGER NOT NULL CHECK (character_count >= 0)`
- `extraction_status VARCHAR(24) NOT NULL` — e.g. `extracted`, `empty`, `unsupported`
- `metadata JSONB NOT NULL DEFAULT '{}'::jsonb`
- `created_at TIMESTAMPTZ NOT NULL`

Constraint/index: `UNIQUE (document_id, page_number)`.

#### `document_chunks`
- `id UUID PRIMARY KEY`
- `document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE`
- `chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0)`
- `text_content TEXT NOT NULL`
- `page_numbers INTEGER[] NOT NULL`
- `start_char INTEGER NULL`
- `end_char INTEGER NULL`
- `token_count INTEGER NULL`
- `metadata JSONB NOT NULL DEFAULT '{}'::jsonb`
- `created_at TIMESTAMPTZ NOT NULL`

Constraints/indexes:
- `UNIQUE (document_id, chunk_index)`.
- GIN index on `page_numbers` only if page-filter queries justify it.
- Index `(document_id, chunk_index)`.
- Ensure `page_numbers` is non-empty and contains valid source pages at application level or with a database check where practical.

#### `chunk_embeddings`
- `id UUID PRIMARY KEY`
- `chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE`
- `provider VARCHAR(80) NOT NULL`
- `model VARCHAR(160) NOT NULL`
- `model_version VARCHAR(120) NULL`
- `dimensions INTEGER NOT NULL CHECK (dimensions > 0)`
- `embedding VECTOR(<DIMENSION>) NOT NULL` — `<DIMENSION>` is a design placeholder and must be replaced by the selected model's fixed dimension in the migration.
- `created_at TIMESTAMPTZ NOT NULL`

Constraints/indexes:
- `UNIQUE (chunk_id, provider, model, model_version)`, adapting NULL handling if needed.
- Vector index appropriate to chosen metric/pgvector version and verified query plan.
- The selected vector dimension must not be left as a literal unresolved placeholder in executable migrations.

#### `query_runs`
- `id UUID PRIMARY KEY`
- `workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
- `question TEXT NOT NULL`
- `selected_document_ids UUID[] NULL` — convenience snapshot only; validate IDs and persist normalized relations if strict relational integrity is required.
- `status VARCHAR(24) NOT NULL` — e.g. `completed`, `insufficient_evidence`, `failed`
- `embedding_provider VARCHAR(80) NULL`
- `embedding_model VARCHAR(160) NULL`
- `llm_provider VARCHAR(80) NULL`
- `llm_model VARCHAR(160) NULL`
- `retrieval_top_k INTEGER NOT NULL`
- `retrieval_threshold DOUBLE PRECISION NULL`
- `latency_ms INTEGER NULL`
- `prompt_tokens INTEGER NULL`
- `completion_tokens INTEGER NULL`
- `error_code VARCHAR(80) NULL`
- `created_at TIMESTAMPTZ NOT NULL`

Index: `(workspace_id, created_at DESC)`. Do not store full prompts or evidence text in logs by default; query history retention should be configurable.

#### `retrieved_evidence`
- `id UUID PRIMARY KEY`
- `query_run_id UUID NOT NULL REFERENCES query_runs(id) ON DELETE CASCADE`
- `chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE`
- `rank INTEGER NOT NULL CHECK (rank >= 1)`
- `distance DOUBLE PRECISION NULL`
- `included_in_context BOOLEAN NOT NULL DEFAULT FALSE`
- `created_at TIMESTAMPTZ NOT NULL`

Constraints/indexes: `UNIQUE (query_run_id, rank)` and optionally `UNIQUE (query_run_id, chunk_id)`.

#### `answers`
- `id UUID PRIMARY KEY`
- `query_run_id UUID NOT NULL UNIQUE REFERENCES query_runs(id) ON DELETE CASCADE`
- `status VARCHAR(32) NOT NULL` — `answered`, `insufficient_evidence`, `conflicting_evidence`, `failed`
- `answer_text TEXT NOT NULL`
- `limitations JSONB NOT NULL DEFAULT '[]'::jsonb`
- `policy_version VARCHAR(80) NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`

#### `citations`
- `id UUID PRIMARY KEY`
- `answer_id UUID NOT NULL REFERENCES answers(id) ON DELETE CASCADE`
- `retrieved_evidence_id UUID NOT NULL REFERENCES retrieved_evidence(id) ON DELETE CASCADE`
- `claim_index INTEGER NULL`
- `quote_start_char INTEGER NULL`
- `quote_end_char INTEGER NULL`
- `display_excerpt TEXT NOT NULL`
- `validation_status VARCHAR(24) NOT NULL` — `valid_reference`, `invalid_reference_rejected`, `needs_review`
- `created_at TIMESTAMPTZ NOT NULL`

Citation document ID, filename, and page numbers should be resolved from the linked chunk/document records at response time, not trusted from model-generated fields. The excerpt should be a faithful span or clearly labeled chunk excerpt; do not represent a generated paraphrase as a direct quote.

#### `comparison_runs`
- `id UUID PRIMARY KEY`
- `workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
- `topic TEXT NOT NULL`
- `selected_document_ids UUID[] NOT NULL`
- `status VARCHAR(24) NOT NULL`
- `llm_provider VARCHAR(80) NULL`
- `llm_model VARCHAR(160) NULL`
- `limitations JSONB NOT NULL DEFAULT '[]'::jsonb`
- `latency_ms INTEGER NULL`
- `created_at TIMESTAMPTZ NOT NULL`

Validate at least two distinct ready documents from the same authorized workspace before creating a run. A normalized `comparison_documents` join table is preferred if querying/foreign-key enforcement over selected IDs becomes important.

#### `comparison_findings`
- `id UUID PRIMARY KEY`
- `comparison_run_id UUID NOT NULL REFERENCES comparison_runs(id) ON DELETE CASCADE`
- `document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE`
- `finding_text TEXT NOT NULL`
- `relationship VARCHAR(24) NOT NULL` — `supports`, `differs`, `apparent_contradiction`, `not_comparable`, `insufficient_evidence`
- `citation_ids UUID[] NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL`

For strict referential integrity, replace `citation_ids` with a normalized `comparison_finding_citations` join table before implementation. The normalized form is recommended if comparison findings are persisted as first-class records.

#### `evaluation_cases`
- `id UUID PRIMARY KEY`
- `case_key VARCHAR(160) NOT NULL UNIQUE`
- `version VARCHAR(40) NOT NULL`
- `question TEXT NOT NULL`
- `workspace_fixture_key VARCHAR(160) NOT NULL`
- `expected_source_keys JSONB NOT NULL`
- `expected_answer_characteristics JSONB NOT NULL`
- `should_abstain BOOLEAN NOT NULL DEFAULT FALSE`
- `enabled BOOLEAN NOT NULL DEFAULT TRUE`
- `created_at TIMESTAMPTZ NOT NULL`

#### `evaluation_runs`
- `id UUID PRIMARY KEY`
- `version VARCHAR(40) NOT NULL`
- `configuration JSONB NOT NULL`
- `status VARCHAR(24) NOT NULL`
- `summary JSONB NOT NULL DEFAULT '{}'::jsonb`
- `started_at TIMESTAMPTZ NOT NULL`
- `completed_at TIMESTAMPTZ NULL`

#### `evaluation_results`
- `id UUID PRIMARY KEY`
- `evaluation_run_id UUID NOT NULL REFERENCES evaluation_runs(id) ON DELETE CASCADE`
- `evaluation_case_id UUID NOT NULL REFERENCES evaluation_cases(id)`
- `retrieval_hit BOOLEAN NULL`
- `citation_validity DOUBLE PRECISION NULL`
- `abstention_correct BOOLEAN NULL`
- `answer_quality_label VARCHAR(80) NULL`
- `judge_type VARCHAR(40) NULL` — e.g. `human`, `rule_based`, `llm_judged`
- `details JSONB NOT NULL DEFAULT '{}'::jsonb`
- `created_at TIMESTAMPTZ NOT NULL`

Constraint: `UNIQUE (evaluation_run_id, evaluation_case_id)`.

### 9.4 Schema notes and migration rules

- The table definitions are logical design contracts; exact SQLAlchemy mappings and migration syntax are implementation details.
- Enable `pgcrypto` only if database-generated UUIDs are chosen; otherwise generate UUIDs in the application.
- Enable pgvector with a versioned migration and test against the chosen PostgreSQL image.
- Use `TIMESTAMPTZ` and UTC timestamps.
- Add foreign keys and cascade behaviour intentionally; deleting a workspace should not leave orphaned pages/chunks/evidence.
- Original file deletion must be coordinated with relational deletion and storage cleanup; database cascades cannot delete filesystem objects.
- Do not store a vector as JSON or a generic array.
- Avoid persisting redundant document/page fields in citations unless they are deliberate immutable snapshots.
- The schema includes query and evaluation history for traceability, but retention and deletion policies must be explicit.
- If the MVP needs less persistence, the implementation may omit `comparison_findings` or some evaluation-run detail only if the requirements remain testable and the omission is documented.

## 10. API Contract

### 10.1 Conventions

- Base path: `/api/v1`.
- Request and response bodies: JSON, except file upload (`multipart/form-data`).
- Identifiers: UUID strings.
- Timestamps: ISO 8601 UTC.
- Validation: Pydantic request/response models; reject unknown or malformed inputs according to a documented policy.
- All list endpoints use bounded pagination.
- Error responses use a consistent envelope.
- OpenAPI generated by FastAPI is the executable API reference.
- All workspace/document scope checks are performed on the server.
- The examples below are normative shape examples; exact field naming should be held consistent between Pydantic schemas, OpenAPI, and frontend types.

### 10.2 Standard error envelope

```json
{
  "error": {
    "code": "DOCUMENT_NOT_READY",
    "message": "This document is still being processed.",
    "request_id": "cfe4f6a8-7d0b-4f1c-90e4-4f7c5e1d2a11",
    "details": {}
  }
}
```

Rules:
- `code` is stable and machine-readable.
- `message` is safe for end users.
- `request_id` supports log correlation.
- `details` contains safe validation information only; never include stack traces, provider secrets, raw prompts, or raw provider payloads.

### 10.3 Health endpoints

#### `GET /api/v1/health`
Liveness check; indicates the API process is running.

**200**
```json
{ "status": "ok" }
```

#### `GET /api/v1/ready`
Readiness check for required dependencies.

**200**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "vector_extension": "ok"
  }
}
```

Use `503 SERVICE_UNAVAILABLE` if required dependencies are not ready. Do not expose internal connection strings or credentials.

### 10.4 Workspaces

#### `POST /api/v1/workspaces`
Create a workspace.

Request:
```json
{
  "name": "Research Papers",
  "description": "Reports for the project"
}
```

Response `201`:
```json
{
  "id": "9bafc4d4-0a6f-4e5c-ae7a-08c0a6a4d93a",
  "name": "Research Papers",
  "description": "Reports for the project",
  "created_at": "2026-10-12T10:00:00Z",
  "updated_at": "2026-10-12T10:00:00Z"
}
```

Validation: trimmed name required, 1–160 characters.

#### `GET /api/v1/workspaces`
List accessible workspaces.

Query: `limit` (default 20, maximum 100), `cursor` (optional).

Response `200`:
```json
{
  "items": [
    {
      "id": "9bafc4d4-0a6f-4e5c-ae7a-08c0a6a4d93a",
      "name": "Research Papers",
      "description": "Reports for the project",
      "created_at": "2026-10-12T10:00:00Z",
      "updated_at": "2026-10-12T10:00:00Z"
    }
  ],
  "next_cursor": null
}
```

#### `GET /api/v1/workspaces/{workspace_id}`
Return one accessible workspace or `404 WORKSPACE_NOT_FOUND`.

#### `DELETE /api/v1/workspaces/{workspace_id}`
Delete the workspace and all associated records and source files according to the deletion policy.

Response `204 No Content`. If cleanup cannot be completed, return a stable error and record/retry cleanup; do not falsely report full deletion.

### 10.5 Documents

#### `POST /api/v1/workspaces/{workspace_id}/documents`
Upload one PDF.

Content type: `multipart/form-data`
- `file`: required PDF file.

Response `202 Accepted`:
```json
{
  "id": "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0",
  "workspace_id": "9bafc4d4-0a6f-4e5c-ae7a-08c0a6a4d93a",
  "filename": "testing-report.pdf",
  "size_bytes": 428193,
  "status": "queued",
  "uploaded_at": "2026-10-12T10:05:00Z",
  "status_url": "/api/v1/workspaces/9bafc4d4-0a6f-4e5c-ae7a-08c0a6a4d93a/documents/7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0"
}
```

Possible errors: `400 INVALID_FILE`, `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_MEDIA_TYPE`, `409 DUPLICATE_DOCUMENT`, `404 WORKSPACE_NOT_FOUND`.

#### `POST /api/v1/workspaces/{workspace_id}/documents/batch`
Upload multiple PDFs. Use repeated `files` multipart fields. Enforce a configured batch count and aggregate size limit.

Response `202`:
```json
{
  "items": [
    {
      "id": "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0",
      "filename": "testing-report.pdf",
      "status": "queued"
    }
  ],
  "rejected": [
    {
      "filename": "notes.txt",
      "error": {
        "code": "UNSUPPORTED_MEDIA_TYPE",
        "message": "Only supported PDF files can be uploaded."
      }
    }
  ]
}
```

Choose either atomic batch rejection or per-file partial acceptance and document it. This design recommends per-file results so one invalid file does not silently discard valid uploads.

#### `GET /api/v1/workspaces/{workspace_id}/documents`
List documents in the workspace.

Query: `status` optional, `limit` default 20/max 100, `cursor` optional.

Response `200`:
```json
{
  "items": [
    {
      "id": "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0",
      "filename": "testing-report.pdf",
      "size_bytes": 428193,
      "page_count": 18,
      "chunk_count": 42,
      "status": "ready",
      "error_code": null,
      "error_message": null,
      "uploaded_at": "2026-10-12T10:05:00Z",
      "processed_at": "2026-10-12T10:05:09Z"
    }
  ],
  "next_cursor": null
}
```

#### `GET /api/v1/workspaces/{workspace_id}/documents/{document_id}`
Return document metadata and processing status.

#### `GET /api/v1/workspaces/{workspace_id}/documents/{document_id}/pages/{page_number}`
Return extracted page text for source inspection, after checking workspace scope.

Response `200`:
```json
{
  "document_id": "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0",
  "filename": "testing-report.pdf",
  "page_number": 3,
  "text": "Extracted source text...",
  "extraction_status": "extracted"
}
```

#### `GET /api/v1/workspaces/{workspace_id}/documents/{document_id}/chunks`
List chunks for debugging/evidence inspection; apply pagination and avoid returning all text by default unless requested.

#### `POST /api/v1/workspaces/{workspace_id}/documents/{document_id}/retry`
Retry a failed ingestion, idempotently.

Response `202`:
```json
{
  "document_id": "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0",
  "status": "queued"
}
```

#### `DELETE /api/v1/workspaces/{workspace_id}/documents/{document_id}`
Delete original file and all dependent page/chunk/embedding records. Response `204`. Authorization and cleanup must be enforced server-side.

### 10.6 Semantic retrieval

#### `POST /api/v1/workspaces/{workspace_id}/search`
Search for evidence without generating an answer.

Request:
```json
{
  "query": "What limitations were found during testing?",
  "document_ids": [
    "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0"
  ],
  "top_k": 5,
  "similarity_threshold": null
}
```

Response `200`:
```json
{
  "query": "What limitations were found during testing?",
  "items": [
    {
      "evidence_id": "3a0c2f74-05b2-4b2e-b0e7-93d3cc38d7f5",
      "document_id": "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0",
      "filename": "testing-report.pdf",
      "page_numbers": [3],
      "chunk_id": "2c00c1e7-3b90-4dbe-bde2-f3fd7a16d110",
      "chunk_index": 7,
      "excerpt": "The test results indicate limitations under low-light conditions...",
      "rank": 1,
      "distance": 0.21
    }
  ]
}
```

Validation: query length bounded; `top_k` constrained to configured min/max; selected documents must belong to the workspace and be ready. Similarity threshold semantics must match the selected metric and must be calibrated with evaluation data.

### 10.7 Question answering

#### `POST /api/v1/workspaces/{workspace_id}/questions`
Retrieve evidence and generate a grounded answer.

Request:
```json
{
  "question": "What limitations were found during testing?",
  "document_ids": [
    "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0"
  ],
  "top_k": 5
}
```

Response `200`:
```json
{
  "query_run_id": "eeb68f52-cdbc-4a8c-b7c8-f9b127da3f5a",
  "status": "answered",
  "answer": "The report identifies limitations under low-light conditions.",
  "limitations": [],
  "citations": [
    {
      "citation_id": "9c706c80-6951-4937-9960-7b46c47c0f1a",
      "document_id": "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0",
      "filename": "testing-report.pdf",
      "page_numbers": [3],
      "excerpt": "The test results indicate limitations under low-light conditions...",
      "claim_index": 0,
      "reference_valid": true
    }
  ],
  "retrieved_evidence_count": 5,
  "usage": {
    "prompt_tokens": 1200,
    "completion_tokens": 160
  },
  "latency_ms": 1820
}
```

Insufficient evidence is a successful domain outcome, not a server error:
```json
{
  "query_run_id": "eeb68f52-cdbc-4a8c-b7c8-f9b127da3f5a",
  "status": "insufficient_evidence",
  "answer": "The selected documents do not provide enough evidence to answer this question.",
  "limitations": [
    "No retrieved passage adequately supports a direct answer."
  ],
  "citations": [],
  "retrieved_evidence_count": 0,
  "usage": null,
  "latency_ms": 240
}
```

Other statuses may include `conflicting_evidence` when supported sources disagree and the disagreement cannot be responsibly collapsed into one answer. Never return a normal `answered` status when the answer service has failed to produce a valid structured response.

### 10.8 Cross-document comparison

#### `POST /api/v1/workspaces/{workspace_id}/comparisons`
Request:
```json
{
  "topic": "Testing limitations",
  "document_ids": [
    "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0",
    "b94fdd0a-0a21-4a11-9f89-8a5a0d5dce42"
  ],
  "top_k_per_document": 3
}
```

Validation: at least two distinct, ready documents in the same workspace.

Response `200`:
```json
{
  "comparison_run_id": "60bde7dc-50f2-4a0b-9f9f-8e9b3f7dd3b7",
  "status": "completed",
  "topic": "Testing limitations",
  "findings": [
    {
      "document_id": "7cb17d7e-0c45-42a9-b2b7-2c2f5c7c17c0",
      "filename": "testing-report.pdf",
      "finding": "Reports reduced performance under low-light conditions.",
      "relationship": "supports",
      "citations": [
        {
          "citation_id": "9c706c80-6951-4937-9960-7b46c47c0f1a",
          "page_numbers": [3],
          "excerpt": "The test results indicate limitations under low-light conditions..."
        }
      ]
    }
  ],
  "overall_summary": "The documents address testing limitations, but their test conditions should be checked before treating the findings as directly comparable.",
  "limitations": [
    "The documents may use different test conditions."
  ]
}
```

Allowed relationship labels should be defined centrally and include a non-committal option such as `not_comparable` or `insufficient_evidence`. Do not infer contradiction merely because wording differs.

### 10.9 Evaluation

#### `GET /api/v1/evaluations/latest`
Return the latest persisted evaluation summary, if one exists.

#### `GET /api/v1/evaluations/runs/{run_id}`
Return a specific evaluation summary and per-case results.

#### `POST /api/v1/evaluations/runs`
Optional demo-only endpoint to trigger an evaluation. **Recommendation:** keep execution in a CLI for the MVP and expose read-only result endpoints only if a UI needs them. Do not allow arbitrary users to trigger expensive provider calls without authorization/rate limits.

Example summary:
```json
{
  "run_id": "c70e6df8-1db3-4d62-ae0a-8a79b6ad4a31",
  "status": "completed",
  "case_count": 20,
  "retrieval_hit_rate": 0.85,
  "citation_validity_rate": 1.0,
  "abstention_accuracy": 0.9,
  "llm_judged_metrics": {
    "enabled": false,
    "label": "Not run"
  },
  "started_at": "2026-10-12T11:00:00Z",
  "completed_at": "2026-10-12T11:00:18Z"
}
```

Metrics must include definitions and denominators. Do not publish numbers as general quality guarantees.

### 10.10 API status/error code catalogue

| HTTP | Error code | Meaning |
|---|---|---|
| 400 | `INVALID_FILE` | Corrupt, malformed, encrypted, or otherwise invalid PDF |
| 400 | `VALIDATION_ERROR` | Request failed validation |
| 401 | `UNAUTHENTICATED` | Authentication required, if auth is enabled |
| 403 | `FORBIDDEN` | Caller is not allowed to access the resource |
| 404 | `WORKSPACE_NOT_FOUND` / `DOCUMENT_NOT_FOUND` | Resource is absent or intentionally concealed |
| 409 | `DUPLICATE_DOCUMENT` | Same file already exists in the workspace |
| 409 | `DOCUMENT_NOT_READY` | Document cannot be queried yet |
| 413 | `FILE_TOO_LARGE` | File exceeds configured limit |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Unsupported upload type |
| 422 | `INSUFFICIENT_DOCUMENT_SCOPE` | Selection is invalid for the requested operation |
| 429 | `RATE_LIMITED` | Rate limit reached, if rate limiting is enabled |
| 502 | `AI_PROVIDER_ERROR` | Upstream AI provider failed or returned invalid output |
| 503 | `DEPENDENCY_UNAVAILABLE` | Required dependency is unavailable |
| 500 | `INTERNAL_ERROR` | Unexpected safe-to-report server error |

Do not use an HTTP 500 response for a normal insufficient-evidence result. Avoid leaking whether another user's resource exists.

## 11. RAG, Citation Validation, and Evidence Policy

### 11.1 Retrieval design

1. Validate the question and workspace/document scope.
2. Generate query embedding with the configured embedding provider.
3. Verify vector dimension/model compatibility.
4. Run a parameterized pgvector similarity query joined to chunks/documents.
5. Filter by workspace and selected ready documents before ranking/limiting results.
6. Return ranked passages with server-derived filename, page numbers, chunk ID, and distance.
7. Record enough metadata for repeatable evaluation while respecting logging/privacy policy.

A basic SQL shape (illustrative only; adapt to actual model names and pgvector operators):

```sql
SELECT
    c.id AS chunk_id,
    c.document_id,
    c.page_numbers,
    c.chunk_index,
    c.text_content,
    e.embedding <=> :query_embedding AS distance
FROM document_chunks AS c
JOIN chunk_embeddings AS e ON e.chunk_id = c.id
JOIN documents AS d ON d.id = c.document_id
WHERE d.workspace_id = :workspace_id
  AND d.status = 'ready'
  AND (:document_ids_is_null OR d.id = ANY(:document_ids))
ORDER BY e.embedding <=> :query_embedding
LIMIT :top_k;
```

This query is a design sketch, not copy-ready SQL. Ensure the vector operator matches the selected distance metric and the selected provider's embedding model.

### 11.2 Evidence context construction

- Keep each evidence item associated with an internal evidence key, chunk ID, document ID, page list, and excerpt.
- Include only the top-ranked, scope-valid passages that fit the configured context budget.
- Preserve source text faithfully; use explicit delimiters and label it as untrusted source content.
- Keep question and system policy separate from source text.
- Avoid adding instructions from the PDF into the system prompt.
- Avoid sending unnecessary personal/sensitive data to external providers; document the selected provider's data-handling settings before use.

### 11.3 Structured answer shape

The provider-facing response should conform to a schema equivalent to:

```json
{
  "status": "answered | insufficient_evidence | conflicting_evidence",
  "answer": "string",
  "claims": [
    {
      "text": "string",
      "evidence_keys": ["E1", "E2"]
    }
  ],
  "limitations": ["string"]
}
```

This is a model-output schema. The API response is assembled by the backend after validation; it must not expose arbitrary model-generated citation metadata as authoritative.

### 11.4 Citation validation algorithm

1. Create an allowlist of evidence keys included in the prompt.
2. Parse the LLM response against the expected schema.
3. For every claim citation, confirm the evidence key is in the allowlist.
4. Reject unknown keys; do not attempt to “repair” them by guessing a document or page.
5. Resolve chunk/document/page metadata from trusted database records.
6. Ensure the cited evidence belongs to the authorized workspace and current query scope.
7. Construct the response citation using server-derived fields.
8. If all citations are invalid, or a substantive answer claim has no acceptable supporting evidence, downgrade the answer to insufficient evidence or a safe validation failure according to the policy.
9. Record citation validity for evaluation.

**Important:** this proves that a reference points to retrieved evidence. It does not prove the passage entails the claim. Entailment/support assessment is a separate, fallible evaluation/policy problem.

### 11.5 Evidence insufficiency policy

Use a deterministic, testable policy before relying on an LLM's self-assessment.

- No ready documents in scope: return a clear scope/processing message; do not call the LLM.
- No retrieved chunks: return `insufficient_evidence`.
- Retrieval candidates all fail the configured relevance threshold: return `insufficient_evidence`.
- Evidence exists but does not answer the specific question: prompt the model to state the gap; if it cannot cite support for the answer, abstain.
- Sources materially disagree: return `conflicting_evidence` or describe each supported position with separate citations and explicit uncertainty.
- Evidence discusses different populations, dates, definitions, or test conditions: mark the comparison as limited/not comparable rather than forcing a single conclusion.
- Provider timeout, malformed structured output, or service outage: return a safe operational error, not a fabricated answer.

Thresholds must be calibrated on the curated evaluation set. Similarity distance is not a probability; do not present it as calibrated confidence. Keep policy version/configuration with query/evaluation metadata.

### 11.6 Prompt-injection defence

- Treat PDF text as data, never as executable instructions.
- Do not expose arbitrary tools or unrestricted network access to the LLM.
- Use a fixed system instruction and delimit retrieved passages.
- Tell the model to ignore instructions found inside passages and to use them only as evidence.
- Validate all model output server-side.
- Test adversarial documents containing text such as “ignore previous instructions” and requests to reveal secrets.
- Prompting is only one defence; enforce scope, tools, citations, and secrets isolation in code.

## 12. Configuration, Secrets, Logging, and Error Handling

### 12.1 Configuration

Use typed settings loaded from environment variables. Validate required values on startup and fail with a safe, actionable message if required configuration is missing.

Suggested backend variables:

```dotenv
APP_ENV=development
APP_NAME=ProofLens AI
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg://prooflens:prooflens_local_only@localhost:5432/prooflens
FILE_STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./var/uploads
MAX_UPLOAD_BYTES=20971520
MAX_BATCH_FILES=10
MAX_PDF_PAGES=500
CHUNK_SIZE_TOKENS=800
CHUNK_OVERLAP_TOKENS=120
RETRIEVAL_TOP_K_DEFAULT=5
RETRIEVAL_TOP_K_MAX=20
RETRIEVAL_DISTANCE_THRESHOLD=
LLM_PROVIDER=google_gemini
LLM_MODEL=gemini-3.8-flash
EMBEDDING_PROVIDER=google_gemini
EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_DIMENSION=768
GEMINI_API_KEY=replace_with_your_gemini_api_key
PROVIDER_TIMEOUT_SECONDS=30
PROVIDER_MAX_RETRIES=2
LOG_LEVEL=INFO
```

Values are examples, not final production limits. The sample database credentials are local-only and must never be reused in production. Add provider-specific variables only for the chosen integration. Do not check a populated `.env` into source control.

Suggested frontend variable:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

This URL is public configuration, not a secret. If frontend server-side requests need a private internal URL, use a separate non-public variable.

### 12.1.1 Environment-driven configuration policy

**Runtime behaviour must be configurable without editing source code.** Use typed settings (`pydantic-settings`) and validate them at application startup. Environment variables should control deployment-specific values, provider selection, credentials, database/storage locations, timeouts, limits, logging, and feature toggles. Keep stable domain rules in typed policy/configuration modules with environment overrides only where operationally justified; do not scatter raw `os.getenv()` calls throughout business logic.

Use a single documented naming convention (`UPPER_SNAKE_CASE`) and explicit defaults. Required settings must fail fast with a message naming the missing variable but never printing its value. Validate cross-field constraints at startup, including:
- the selected embedding model's configured dimension matches the database vector column/index;
- production mode rejects development defaults and insecure placeholder credentials;
- upload, page, batch, chunk, retrieval, timeout, and retry limits are positive and bounded;
- provider credentials are present when the corresponding external provider is enabled;
- CORS origins are explicit, not wildcarded with credentials;
- local filesystem storage paths resolve to an approved writable directory;
- debug mode and verbose provider/prompt logging are disabled in production.

Recommended configuration catalogue. Gemini is the selected provider for both APIs; keep provider-neutral settings so the internal adapters can be replaced later if explicitly approved:

| Variable | Purpose | Secret? | Guidance |
|---|---|---:|---|
| `APP_ENV` | `development`, `test`, or `production` | No | Required; controls safe defaults, never use a client-provided value |
| `APP_NAME` | Service display/name | No | Default `ProofLens AI` |
| `DEBUG` | Debug behaviour | No | Default false; must be false in production |
| `API_V1_PREFIX` | Versioned API prefix | No | Default `/api/v1` |
| `DATABASE_URL` | Backend DB connection | **Yes** if it contains credentials | Backend only; use separate test DB in tests |
| `DB_POOL_SIZE` | SQLAlchemy pool size | No | Bounded positive integer |
| `DB_MAX_OVERFLOW` | Maximum overflow connections | No | Bounded non-negative integer |
| `DB_POOL_TIMEOUT_SECONDS` | DB pool acquisition timeout | No | Bounded duration |
| `FILE_STORAGE_BACKEND` | `local` initially | No | Reject unsupported values |
| `LOCAL_STORAGE_PATH` | Private upload directory | No | Must not be web-served or user-controlled |
| `MAX_UPLOAD_BYTES` | Per-file byte limit | No | Enforce in API and proxy/container limits |
| `MAX_BATCH_FILES` | Batch upload limit | No | Positive bounded integer |
| `MAX_PDF_PAGES` | Per-PDF page limit | No | Reject over-limit PDFs before expensive processing |
| `PDF_TEXT_MIN_CHARS_PER_PAGE` | Empty/scanned-page detection heuristic | No | Heuristic only; does not constitute OCR |
| `CHUNK_SIZE_TOKENS` | Target chunk size | No | Positive bounded integer |
| `CHUNK_OVERLAP_TOKENS` | Chunk overlap | No | Must be smaller than chunk size |
| `RETRIEVAL_TOP_K_DEFAULT` | Default number of passages | No | Must not exceed configured maximum |
| `RETRIEVAL_TOP_K_MAX` | Hard retrieval result cap | No | Enforced server-side regardless of request |
| `RETRIEVAL_DISTANCE_THRESHOLD` | Optional retrieval cutoff | No | Calibrate for chosen embedding/distance metric; blank means disabled |
| `LLM_PROVIDER` | Selected LLM adapter | No | Allowlist supported adapters |
| `LLM_MODEL` | Model identifier | No | Never accept arbitrary model overrides from public requests by default |
| `GEMINI_API_KEY` | Google Gemini API credential shared by the LLM and embedding adapters | **Yes** | Backend runtime secret only; never expose to the browser or commit it to Git |
| `LLM_BASE_URL` | Provider endpoint override | Potentially | Restrict/allowlist to avoid SSRF or credential exfiltration |
| `LLM_TIMEOUT_SECONDS` | LLM request timeout | No | Bounded duration |
| `LLM_MAX_RETRIES` | Retry cap | No | Small bounded integer |
| `LLM_MAX_OUTPUT_TOKENS` | Generation output cap | No | Enforced server-side |
| `EMBEDDING_PROVIDER` | Selected embedding adapter | No | Allowlist supported adapters |
| `EMBEDDING_MODEL` | Embedding model identifier | No | Must match the stored vector space/version |
| `EMBEDDING_DIMENSION` | Vector dimension | No | Must match DB schema; migration required to change it |
| `EMBEDDING_BATCH_SIZE` | Maximum texts per embedding request | No | Respect provider limits |
| `PROVIDER_TIMEOUT_SECONDS` | Shared provider timeout if not overridden | No | Bounded duration |
| `PROVIDER_MAX_RETRIES` | Shared retry cap if not overridden | No | Avoid nested retry policies |
| `CORS_ORIGINS` | Explicit allowed browser origins | No | Comma-separated or structured list; no permissive production wildcard |
| `TRUSTED_HOSTS` | Accepted hostnames | No | Configure for deployment topology |
| `RATE_LIMIT_ENABLED` | Toggle request rate limiting | No | If enabled, configure implementation and limits; do not imply distributed limiting without infrastructure |
| `RATE_LIMIT_PER_MINUTE` | Per-identity/IP request cap | No | In-memory limits are single-process only; document that limitation |
| `LOG_LEVEL` | Log verbosity | No | `INFO` default; avoid debug in production |
| `LOG_FORMAT` | `json` or readable local logs | No | Structured JSON recommended in production |
| `LOG_DOCUMENT_CONTENT` | Diagnostic content logging | No | Must default false and be prohibited in production |
| `REQUEST_TIMEOUT_SECONDS` | Overall API request budget | No | Must align with provider and proxy timeout limits |
| `NEXT_PUBLIC_API_BASE_URL` | Browser-visible API URL | No | Public by design; never put credentials in `NEXT_PUBLIC_*` |
| `INTERNAL_API_BASE_URL` | Server-side frontend-to-backend URL if needed | No, unless embedded auth | Must not use `NEXT_PUBLIC_` prefix |

Keep provider-specific configuration explicit. For the selected Gemini integration, both adapters read `GEMINI_API_KEY`; do not duplicate it as separate LLM and embedding secrets. Avoid duplicate aliases for the same setting.

### 12.1.2 Environment files and startup behaviour

- Root `.env.example`, `backend/.env.example`, and `frontend/.env.example` contain **placeholders and non-secret defaults only**. Keep one canonical source for each variable and document which service consumes it.
- Local developers create ignored `.env` files from the examples. Never place real credentials in source files, Markdown docs, Dockerfiles, `docker-compose.yml`, client components, test fixtures, screenshots, or shell history where avoidable.
- Docker Compose may read local environment files, but production secrets must be injected by the deployment platform/secret manager and not baked into images or build arguments.
- Only variables prefixed `NEXT_PUBLIC_` may be exposed intentionally to browser code; these variables are public and must never contain secrets. LLM/embedding credentials and the database URL belong exclusively to the backend.
- Do not serialize all environment settings into a frontend config endpoint. Expose only explicitly approved public settings.
- Redact credentials from connection strings and provider URLs before logging. Never log a settings object wholesale.
- Keep `.env.test` or test secrets local/CI-protected and use isolated test credentials/data. CI should use protected secret variables, not committed files.
- Startup should validate configuration once, construct typed settings, and inject dependencies. Unit tests should inject settings/fakes instead of mutating global process environment wherever practical.
- Changing embedding model or dimension is a data migration event: do not silently query old vectors with a new embedding model. Plan re-embedding/versioning and index migration.

### 12.2 Secrets management

- Store local provider keys in ignored `.env` files or an approved local secret store; commit only `.env.example` with placeholders.
- Keep keys out of browser bundles, client-side code, API responses, error messages, logs, screenshots, documentation, test fixtures, and Git history.
- `NEXT_PUBLIC_*` is never a secret namespace. Do not place `GEMINI_API_KEY`, `DATABASE_URL`, private tokens, or signed storage credentials in it.
- Use deployment secret management when deployed; inject secrets at runtime, not in Docker build arguments, Docker image layers, or committed Compose defaults.
- Apply least privilege, rotate exposed keys immediately, and use separate credentials for development, testing, and production where supported.
- Redact secrets in exception handling and verify dependency/provider logs do not echo request headers or credentials.
- Verify the selected provider's retention/training/data-handling policy before sending document text; external model calls are a data transfer boundary.
- A `.env.example` is documentation, not a secure vault. Example credentials must be clearly local-only and must not work against any remote environment.
- Add automated checks for accidentally committed secrets where practical; never print secret values as part of configuration validation.

### 12.3 Logging and observability

- Emit structured logs with timestamp, level, request ID, route, status, duration, and safe resource IDs.
- Log provider name/model, latency, retry count, token usage, and error category where available.
- Do not log full PDFs, page text, full evidence context, API keys, authorization headers, or raw provider payloads by default.
- Allow explicit, local-only diagnostic logging behind a deliberate setting and ensure it is disabled by default.
- Keep application logs separate from persisted evaluation evidence.
- Include a request/correlation ID in errors and logs.

### 12.4 Error handling and retries

- Map known exceptions to stable error codes and suitable HTTP status codes.
- Return generic safe messages for unexpected errors; detailed stack traces stay in server logs.
- Use bounded timeouts and retries only for transient provider errors (e.g. rate limit/service unavailable) and retry only operations safe to repeat.
- Do not retry invalid inputs or schema violations indefinitely.
- Avoid nested retry loops in both SDK and application code; choose a single documented retry policy.
- Use a transaction boundary for database writes and explicit compensation for filesystem operations.
- Mark provider failures distinctly from insufficient evidence.

## 13. File Storage and Deletion

### 13.1 Storage interface

Define a minimal interface such as:
- `save(upload_stream, document_id) -> storage_key`
- `open(storage_key) -> binary stream`
- `delete(storage_key) -> result`
- optional `exists(storage_key) -> bool`

The local implementation should generate storage keys itself, avoid trusting user-supplied paths, and prevent path traversal. Keep original filenames as metadata only, not as trusted filesystem paths.

### 13.2 Deletion policy

When a document is deleted:
1. Check authorization and workspace ownership.
2. Mark it `deleting` to prevent new retrieval.
3. Remove it from search eligibility immediately.
4. Delete dependent query evidence/citations or retain only de-identified history if a separately approved retention policy permits it.
5. Delete chunks, embeddings, pages, and the original file.
6. Mark it `deleted` or remove the row after cleanup according to the chosen audit policy.
7. If file deletion fails, record a cleanup failure and retry; do not claim successful complete deletion.

The implementation must choose whether historical answers are deleted or retained with source references invalidated. The safer MVP default is to cascade-delete dependent evidence/citations for that document and clearly document the consequence for past query history.

## 14. Local Development and Docker Strategy

### 14.1 Proposed repository layout

```text
prooflens-ai/
├── docs/
│   ├── TECHNICAL-DESIGN.md
│   └── IMPLEMENTATION-PLAN.md        # Create only after this TDD is reviewed
├── backend/
├── frontend/
├── docker-compose.yml
├── .gitignore
├── .env.example                      # Shared/local orchestration placeholders only
└── README.md
```

No application code or project scaffolding is implied by this proposed tree.

### 14.1.1 Complete proposed repository folder structure

The following is the **complete recommended repository layout for the MVP**, including documentation, application code, tests, local infrastructure, developer scripts, and environment templates. It is a target structure, not a command to generate every file immediately. Keep modules that are not yet needed out of the initial vertical slice, but preserve the boundaries when their functionality is implemented.

```text
prooflens-ai/
├── README.md
├── LICENSE                         # Add only if a license is selected
├── .gitignore
├── .dockerignore
├── .editorconfig
├── .env.example                    # Safe shared defaults; no real credentials
├── docker-compose.yml              # Local-only development orchestration
├── Makefile                        # Optional convenience wrappers; no hidden logic
├── docs/
│   ├── TECHNICAL-DESIGN.md         # This TDD + SRS
│   ├── IMPLEMENTATION-PLAN.md      # Write only after TDD approval
│   ├── architecture/               # Optional ADRs and diagrams as decisions arise
│   ├── api/                        # Optional generated/exported API examples
│   └── operations/                 # Local runbook and deployment notes as needed
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .env.example                # Backend-specific placeholders; never secrets
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── src/
│   │   └── prooflens/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── deps.py
│   │       │   ├── errors.py
│   │       │   └── v1/
│   │       │       ├── __init__.py
│   │       │       ├── router.py
│   │       │       └── routes/
│   │       │           ├── health.py
│   │       │           ├── workspaces.py
│   │       │           ├── documents.py
│   │       │           ├── search.py
│   │       │           ├── questions.py
│   │       │           ├── comparisons.py
│   │       │           └── evaluations.py
│   │       ├── core/
│   │       │   ├── config.py        # Typed environment settings and validation
│   │       │   ├── logging.py
│   │       │   ├── security.py
│   │       │   ├── middleware.py    # Request IDs, safe headers, timing
│   │       │   └── exceptions.py
│   │       ├── domain/
│   │       │   ├── enums.py
│   │       │   ├── policies.py      # Evidence, abstention, limits
│   │       │   └── errors.py
│   │       ├── schemas/
│   │       │   ├── common.py
│   │       │   ├── workspaces.py
│   │       │   ├── documents.py
│   │       │   ├── search.py
│   │       │   ├── questions.py
│   │       │   ├── comparisons.py
│   │       │   └── evaluations.py
│   │       ├── db/
│   │       │   ├── base.py
│   │       │   ├── session.py
│   │       │   ├── models/
│   │       │   ├── repositories/
│   │       │   └── migrations_support.py
│   │       ├── services/
│   │       │   ├── workspaces.py
│   │       │   ├── documents.py
│   │       │   ├── ingestion.py
│   │       │   ├── pdf_extraction.py
│   │       │   ├── chunking.py
│   │       │   ├── embeddings.py
│   │       │   ├── retrieval.py
│   │       │   ├── answering.py
│   │       │   ├── citation_validation.py
│   │       │   ├── evidence_sufficiency.py
│   │       │   ├── comparison.py
│   │       │   └── evaluation.py
│   │       ├── providers/
│   │       │   ├── llm/
│   │       │   │   ├── base.py
│   │       │   │   └── selected_provider.py
│   │       │   └── embeddings/
│   │       │       ├── base.py
│   │       │       └── selected_provider.py
│   │       └── storage/
│   │           ├── base.py
│   │           └── local_filesystem.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── api/
│   │   ├── security/
│   │   ├── fixtures/
│   │   │   └── pdfs/                # Synthetic or approved, non-sensitive PDFs
│   │   └── evaluation/
│   └── scripts/
│       ├── seed_demo.py
│       └── run_evaluation.py
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── eslint.config.mjs            # Or compatible config chosen at setup
│   ├── postcss.config.mjs
│   ├── .env.example
│   ├── Dockerfile
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── error.tsx
│   │   │   ├── loading.tsx
│   │   │   ├── not-found.tsx
│   │   │   └── workspaces/
│   │   │       ├── page.tsx
│   │   │       └── [workspaceId]/
│   │   │           ├── page.tsx
│   │   │           ├── documents/
│   │   │           │   └── [documentId]/page.tsx
│   │   │           ├── ask/page.tsx
│   │   │           ├── compare/page.tsx
│   │   │           └── evaluation/page.tsx
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── workspaces/
│   │   │   ├── documents/
│   │   │   ├── upload/
│   │   │   ├── questions/
│   │   │   ├── evidence/
│   │   │   ├── comparison/
│   │   │   ├── evaluation/
│   │   │   ├── feedback/
│   │   │   └── ui/
│   │   ├── hooks/
│   │   ├── lib/
│   │   │   ├── api-client.ts
│   │   │   ├── api-types.ts
│   │   │   ├── validators.ts
│   │   │   └── formatters.ts
│   │   └── styles/
│   ├── tests/
│   │   ├── components/
│   │   └── e2e/
│   └── next-env.d.ts
├── infra/
│   └── postgres/
│       └── init/                    # Optional extension/init SQL only if needed
├── scripts/
│   ├── check-env.example            # Optional safe config validation helper
│   └── dev-reset.sh                 # Optional, destructive actions require confirmation
└── var/                             # Runtime-created local data; ignored by Git
    ├── uploads/
    └── evaluation-results/
```

**Repository rules:**
- Do not commit `var/`, real `.env` files, uploaded customer PDFs, generated secrets, provider responses containing document text, or private evaluation outputs.
- Keep migrations in `backend/alembic/versions/`; never rely on ORM auto-create for deployed environments.
- Keep the OpenAPI contract generated from FastAPI schemas and test that frontend types remain aligned; do not manually duplicate incompatible contracts.
- Add files only when implemented; this tree describes boundaries and intended destinations, not a requirement for empty placeholder files.
- If the chosen package manager differs, keep exactly one committed lockfile for that manager and update this design consistently.

### 14.2 Docker Compose services

**MVP local Compose services**
- `db`: PostgreSQL image with a compatible pgvector extension, persistent named volume, health check, and local-only credentials.
- `backend`: FastAPI service, dependent on DB health, with source mounted for development if hot reload is desired.
- `frontend`: Next.js development server, dependent on backend availability as needed.

A single custom database image or a verified PostgreSQL/pgvector image may be selected; pin image tags rather than using `latest`. Verify the exact image supports the desired PostgreSQL and pgvector versions.

**Do not add initially:** Redis, a queue broker, separate vector database, Kubernetes, or object-storage emulator unless a documented requirement justifies it.

### 14.3 Local startup sequence

1. Copy `.env.example` to local environment files and set provider credentials locally.
2. Start PostgreSQL/pgvector using Docker Compose.
3. Wait for the database health check.
4. Install backend dependencies from the committed lockfile.
5. Run Alembic migrations.
6. Start FastAPI.
7. Install frontend dependencies from the committed lockfile.
8. Start Next.js.
9. Verify `/api/v1/health`, `/api/v1/ready`, frontend workspace creation, upload, question answering, citation inspection, and insufficient-evidence behaviour.
10. Run unit, integration, and evaluation commands.

Exact commands should be documented in the README when the actual files and package scripts are created. Do not claim these commands have already been run.

### 14.4 Environment separation

- Development database and local uploaded files are disposable and local-only.
- Tests should use an isolated test database and synthetic/approved PDF fixtures.
- Evaluation fixtures should not depend on live user uploads.
- Production storage, auth, TLS, backups, monitoring, and deployment are future decisions; do not imply Docker Compose alone makes the app production-ready.

## 15. Testing Strategy

### 15.1 Unit tests

Use fake providers and isolated fixtures to test:
- PDF page extraction result mapping and empty-page handling.
- Chunk boundaries, overlap, page-number preservation, and stable chunk indices.
- File validation, checksum duplicate policy, and storage key safety.
- Embedding response count and dimension validation.
- Retrieval parameter validation and workspace/document scope construction.
- Structured LLM response parsing.
- Citation allowlist validation and server-side metadata resolution.
- Evidence insufficiency and conflicting-evidence policies.
- Comparison label validation and non-comparable-scope handling.
- Error mapping and retry classification.
- Deletion orchestration and partial cleanup outcomes.

### 15.2 Integration tests

Use a real isolated PostgreSQL + pgvector database for:
- Alembic migrations from an empty database.
- Workspace/document/page/chunk/embedding persistence.
- Vector query ordering and workspace/document filtering.
- End-to-end ingestion from a fixture PDF to a ready document.
- Question flow using fake LLM/embedding adapters, including citations and abstention.
- Document/workspace deletion and cascade behaviour.
- Provider outage/timeout mapping without leaking secrets.

Keep external API calls out of default CI tests. A separate opt-in smoke test may call real providers, require explicit credentials, and report cost/usage.

### 15.3 API tests

Verify:
- Request schemas, bounds, and stable error envelopes.
- Correct status codes for upload, duplicate, not-ready, and invalid-scope operations.
- Pagination limits.
- Workspace/document authorization or demo-mode constraints.
- Citation source fields are derived from persisted evidence.
- No endpoint returns provider secrets, filesystem paths, or stack traces.

### 15.4 Frontend tests

- Component tests for upload status, empty/error states, citations, insufficient evidence, and comparison caveats.
- API client error parsing.
- E2E critical path: create workspace → upload fixture PDF → wait for ready → ask question → open citation.
- E2E unsupported question → see insufficient-evidence state.
- E2E compare two documents → see findings and source citations.
- Keyboard navigation and basic accessibility checks.

### 15.5 AI evaluation

Keep a small version-controlled dataset with:
- stable case key and version;
- fixture workspace/document set;
- question;
- expected source documents/pages or evidence keys;
- expected answer characteristics;
- whether abstention is expected.

Required metrics:
- **Retrieval hit rate:** proportion of cases where at least one expected evidence source appears in the top-k retrieval set. Define the denominator and expected-source matching rule.
- **Citation validity rate:** valid cited references divided by all generated citation references, plus a count of answers with invalid citations.
- **Abstention accuracy:** correct abstention/non-abstention outcomes on cases labeled for this behaviour; report false abstentions and unsupported answers separately where practical.

Optional:
- Human-reviewed answer support score.
- LLM-judged relevance/faithfulness, clearly labeled model-based, with evaluator model/version recorded.

Evaluation reports should include model/configuration, dataset version, timestamp, counts, metric definitions, and known limitations. Do not claim that an LLM judge establishes ground truth.

### 15.6 Suggested commands (finalize with project configuration)

```bash
# Backend examples; exact commands depend on the committed tooling setup
ruff check .
pytest

# Database migrations
alembic upgrade head

# Frontend examples
npm run lint
npm run test
npm run build

# Evaluation
python -m prooflens.scripts.run_evaluation
```

These are proposed command shapes, not verified commands. Align them with the final package layout and scripts.

## 16. Performance and Capacity Guardrails

The PRD does not specify a deployment environment or measurable latency target. Therefore this document does not promise a numeric response-time SLA.

Define configurable limits before implementation:
- maximum upload bytes;
- maximum files per batch;
- maximum PDF pages;
- maximum extracted text/chunks per document;
- maximum chunk size and overlap;
- maximum embedding batch size;
- maximum retrieval `top_k`;
- maximum evidence context budget;
- maximum generated answer tokens;
- provider timeout and retry count;
- request/body size limits.

Measure ingestion duration, embedding latency, retrieval latency, LLM latency, total query latency, and token usage where available. Optimize only after observing the bottleneck. If ingestion exceeds acceptable request duration or needs restart-safe retries, introduce a durable worker/queue as a separately reviewed architectural change.

## 17. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Invalid/invented citations | Evidence-key allowlist, schema validation, server-derived source metadata, negative tests |
| Relevant passage not retrieved | Curated retrieval set, tune chunking/top-k/threshold, consider reranking only if evidence shows need |
| Fluent but unsupported answer | Evidence sufficiency policy, structured claims/citations, abstention tests |
| Prompt injection in PDF | Treat content as untrusted data, no arbitrary tools, adversarial tests |
| Model dimension changes | Lock model/dimension in config and migration; version embeddings; explicit re-embedding plan |
| Duplicate/partial ingestion | Checksums, stable chunk identity, transaction boundaries, idempotent retry |
| Large/slow PDFs | Upload/page/chunk limits, visible status, background worker only when justified |
| Provider outage/rate limit | Timeouts, bounded retry, safe errors, provider abstraction |
| Local storage loss | Clearly label local storage as development-only; choose durable storage before production |
| Cross-workspace data leak | Server-side scope checks, query filters, negative authorization tests |
| Misleading evaluation | Versioned data, metric definitions, model-based labels, human review for key cases |
| Scope creep | No agents, OCR, web research, queue infrastructure, or enterprise features without explicit approval |

## 18. Future Enhancements (Not MVP Commitments)

Consider only after the core workflow is tested:
- Authentication and multi-user workspace authorization.
- Durable background worker/queue for ingestion.
- Object storage for uploaded documents.
- OCR for scanned PDFs.
- Hybrid keyword + vector retrieval or reranking, if evaluation demonstrates a need.
- Conversation threads and saved query history.
- PDF viewer with page navigation/highlighting.
- More detailed claim-level support review.
- Additional document types/languages.
- Production deployment, monitoring, backups, and retention controls.

Each enhancement needs a concrete user need, architecture impact assessment, and explicit scope approval.

## 19. Decisions Required Before Implementation

The following should be confirmed during TDD review. Conservative defaults can be accepted in writing.

1. **LLM provider/model:** selected as Google Gemini API with initial model `gemini-3.8-flash`; verify availability, pricing, structured-output behavior, and generation limits before implementation.
2. **Embedding provider/model and vector dimension:** selected as Google Gemini API with initial model `gemini-embedding-2` and 768 dimensions; verify API response dimensions and retrieval evaluation before finalizing the migration/index.
3. **Authentication:** single-user local demo versus authenticated multi-user deployment. Multi-user/public use requires server-side authorization.
4. **Limits:** maximum file size, batch count, and PDF page count.
5. **Ingestion execution:** bounded synchronous/in-process processing for a small demo versus durable background worker.
6. **Storage target:** local filesystem for development; production object storage deferred.
7. **Retention:** whether query history and answers are deleted when a source document is deleted.
8. **Vector metric/index:** confirm with selected embedding model and pgvector version.
9. **Frontend test/package choices:** npm versus pnpm; Vitest versus another compatible runner.
10. **Evaluation endpoint:** CLI-only evaluation (recommended) versus a protected UI trigger.

## 20. Design Completion Checklist

Before implementation begins, the owner/reviewer should confirm:

- [ ] Product scope and authoritative ten-step workflow match the PRD.
- [ ] Functional and non-functional requirements are complete for the MVP.
- [x] Provider selected: Google Gemini API for both LLM generation and embeddings. Proposed models: `gemini-3.8-flash` and `gemini-embedding-2` with 768 dimensions, subject to implementation-time verification and evaluation.
- [ ] Database schema, migrations, deletion behaviour, and provenance model are approved.
- [ ] API contracts and error envelope are approved.
- [ ] Evidence sufficiency and citation validation are understood as separate checks.
- [ ] Authentication/demo-mode limitations are explicit.
- [ ] Dependencies and infrastructure are justified and MVP-sized.
- [ ] Testing and evaluation strategy is reproducible.
- [ ] No implementation has been started as a consequence of this design document.
- [ ] After this document is finalized, create `docs/IMPLEMENTATION-PLAN.md` with phases, dependencies, file-level deliverables, acceptance criteria, validation commands, and review gates.

---

## Appendix A — Requirement Traceability

| PRD requirement | TDD coverage |
|---|---|
| FR-01 Workspace/document library | Sections 5, 8, 10 |
| FR-02 Extraction/provenance | Sections 6, 9 |
| FR-03 Chunking/embeddings | Sections 6, 7, 9 |
| FR-04 Semantic retrieval | Sections 6, 10, 11 |
| FR-05 Grounded Q&A | Sections 6, 10, 11 |
| FR-06 Evidence inspection | Sections 8, 10 |
| FR-07 Cross-document comparison | Sections 8, 9, 10, 11 |
| FR-08 Basic evaluation | Sections 9, 10, 15 |
| FR-09 Operational behaviour | Sections 12, 15, 16 |
| Security/privacy NFRs | Sections 4, 11, 12, 13, 15 |
| Reliability/maintainability/performance/accessibility | Sections 7, 8, 12, 15, 16 |
| MVP acceptance criteria | Sections 5.4, 15, 20 |
| Antigravity guardrails | Sections 1, 14, 19, 20 |
