"""Integration tests for Search and Analysis API routes (Milestones 3 and 4)."""

import fitz
from fastapi.testclient import TestClient


def create_sample_pdf(content_pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in content_pages:
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_semantic_search_empty_workspace(client: TestClient) -> None:
    ws_res = client.post("/api/v1/workspaces", json={"name": "Empty WS"})
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    res = client.post(f"/api/v1/workspaces/{ws_id}/search", json={"query": "test query"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_results"] == 0
    assert data["results"] == []


def test_semantic_search_with_indexed_document(client: TestClient) -> None:
    ws_res = client.post("/api/v1/workspaces", json={"name": "Search WS"})
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    pdf_bytes = create_sample_pdf([
        "Page 1: Ingestion and vector search using high-dimensional cosine distance.",
        "Page 2: Grounded citations prevent hallucinations in document QA.",
    ])
    files = {"file": ("manual.pdf", pdf_bytes, "application/pdf")}
    upload_res = client.post(f"/api/v1/workspaces/{ws_id}/documents", files=files)
    assert upload_res.status_code == 202

    # Query search
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/search",
        json={"query": "vector search", "top_k": 5},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_results"] > 0
    first_result = data["results"][0]
    assert "chunk_id" in first_result
    assert "document_id" in first_result
    assert first_result["page_numbers"] != []


def test_grounded_analysis_flow(client: TestClient) -> None:
    ws_res = client.post("/api/v1/workspaces", json={"name": "Analysis WS"})
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    pdf_bytes = create_sample_pdf([
        "Section 1: The ProofLens engine extracts text from PDF pages with PyMuPDF.",
        "Section 2: Citations tie every generated claim back to exact page numbers.",
    ])
    files = {"file": ("report.pdf", pdf_bytes, "application/pdf")}
    upload_res = client.post(f"/api/v1/workspaces/{ws_id}/documents", files=files)
    assert upload_res.status_code == 202

    # Call analyse endpoint
    analyse_res = client.post(
        f"/api/v1/workspaces/{ws_id}/analyse",
        json={"question": "How does ProofLens extract text?", "top_k": 3},
    )
    assert analyse_res.status_code == 200
    data = analyse_res.json()
    assert "[STUB] Answer to: How does ProofLens extract text?" in data["answer"]
    assert data["chunks_used"] > 0
    assert len(data["citations"]) > 0
    assert data["citations"][0]["page_numbers"] != []


def test_analyse_empty_workspace_returns_fallback(client: TestClient) -> None:
    ws_res = client.post("/api/v1/workspaces", json={"name": "Empty Analysis WS"})
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    analyse_res = client.post(
        f"/api/v1/workspaces/{ws_id}/analyse",
        json={"question": "What is the capital of France?"},
    )
    assert analyse_res.status_code == 200
    data = analyse_res.json()
    assert "No relevant content found" in data["answer"]
    assert data["chunks_used"] == 0
    assert data["citations"] == []
