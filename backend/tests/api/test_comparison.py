"""Integration tests for Cross-Document Comparison API route (Milestone 5)."""

import uuid

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


def test_comparison_requires_two_documents(client: TestClient) -> None:
    ws_res = client.post("/api/v1/workspaces", json={"name": "Compare WS"})
    ws_id = ws_res.json()["id"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/compare",
        json={
            "document_ids": [str(uuid.uuid4())],
            "topic": "evaluation metrics",
        },
    )
    assert res.status_code == 400


def test_comparison_with_nonexistent_document(client: TestClient) -> None:
    ws_res = client.post("/api/v1/workspaces", json={"name": "Compare WS 2"})
    ws_id = ws_res.json()["id"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/compare",
        json={
            "document_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "topic": "evaluation metrics",
        },
    )
    assert res.status_code == 404


def test_cross_document_comparison_success(client: TestClient) -> None:
    ws_res = client.post("/api/v1/workspaces", json={"name": "Multi-Doc WS"})
    ws_id = ws_res.json()["id"]

    # Upload Doc 1
    pdf1 = create_sample_pdf([
        "Study A concludes that dense vector search achieves 94% recall on technical documents.",
    ])
    res1 = client.post(
        f"/api/v1/workspaces/{ws_id}/documents",
        files={"file": ("study_a.pdf", pdf1, "application/pdf")},
    )
    assert res1.status_code == 202
    doc1_id = res1.json()["id"]

    # Upload Doc 2
    pdf2 = create_sample_pdf([
        "Study B benchmarks hybrid retrieval and reports improved precision over pure dense models.",
    ])
    res2 = client.post(
        f"/api/v1/workspaces/{ws_id}/documents",
        files={"file": ("study_b.pdf", pdf2, "application/pdf")},
    )
    assert res2.status_code == 202
    doc2_id = res2.json()["id"]

    # Perform comparison
    compare_res = client.post(
        f"/api/v1/workspaces/{ws_id}/compare",
        json={
            "document_ids": [doc1_id, doc2_id],
            "topic": "retrieval performance benchmarks",
            "top_k_per_doc": 2,
        },
    )
    assert compare_res.status_code == 200
    data = compare_res.json()
    assert data["topic"] == "retrieval performance benchmarks"
    assert len(data["documents"]) == 2
    assert data["documents"][0]["document_id"] == doc1_id
    assert data["documents"][1]["document_id"] == doc2_id
    assert len(data["documents"][0]["citations"]) > 0
    assert len(data["documents"][1]["citations"]) > 0
    assert "Cross-document comparison synthesis" in data["synthesis"]
    assert data["relationship"] in ["supports", "differs", "apparent_contradiction", "not_comparable"]
