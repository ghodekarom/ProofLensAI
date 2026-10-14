"""Integration tests for Workspaces and Documents API routes."""

import fitz
from fastapi.testclient import TestClient


def create_sample_pdf(content_pages: list[str]) -> bytes:
    """Helper to generate a real valid PDF in memory."""
    doc = fitz.open()
    for text in content_pages:
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_workspaces_crud_lifecycle(client: TestClient):
    # 1. Create workspace
    payload = {"name": "AI Research Lab", "description": "Workspace for research papers"}
    res = client.post("/api/v1/workspaces", json=payload)
    assert res.status_code == 201
    workspace = res.json()
    assert workspace["name"] == "AI Research Lab"
    assert "id" in workspace
    workspace_id = workspace["id"]

    # 2. List workspaces
    res = client.get("/api/v1/workspaces")
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(w["id"] == workspace_id for w in items)

    # 3. Get workspace
    res = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert res.status_code == 200
    assert res.json()["id"] == workspace_id

    # 4. Delete workspace
    res = client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert res.status_code == 204

    # 5. Verify 404
    res = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "WORKSPACE_NOT_FOUND"


def test_document_upload_and_extraction_pipeline(client: TestClient):
    # Create workspace
    ws_res = client.post("/api/v1/workspaces", json={"name": "Testing Workspace"})
    workspace_id = ws_res.json()["id"]

    # Generate 2-page PDF
    pdf_bytes = create_sample_pdf([
        "Page 1: Findings on Evidence-Grounded Artificial Intelligence systems.",
        "Page 2: Benchmark results demonstrating high retrieval hit rates.",
    ])

    # Upload document
    files = {"file": ("research_paper.pdf", pdf_bytes, "application/pdf")}
    upload_res = client.post(f"/api/v1/workspaces/{workspace_id}/documents", files=files)
    assert upload_res.status_code == 202
    doc_data = upload_res.json()
    document_id = doc_data["id"]
    assert doc_data["filename"] == "research_paper.pdf"

    # In test client, BackgroundTasks execute before response returns
    # Check document status
    doc_res = client.get(f"/api/v1/workspaces/{workspace_id}/documents/{document_id}")
    assert doc_res.status_code == 200
    doc_detail = doc_res.json()
    assert doc_detail["status"] == "ready"
    assert doc_detail["page_count"] == 2

    # Verify Page 1 inspection
    p1_res = client.get(f"/api/v1/workspaces/{workspace_id}/documents/{document_id}/pages/1")
    assert p1_res.status_code == 200
    p1 = p1_res.json()
    assert p1["page_number"] == 1
    assert "Page 1: Findings on Evidence-Grounded" in p1["text"]

    # Verify Page 2 inspection
    p2_res = client.get(f"/api/v1/workspaces/{workspace_id}/documents/{document_id}/pages/2")
    assert p2_res.status_code == 200
    p2 = p2_res.json()
    assert p2["page_number"] == 2
    assert "Page 2: Benchmark results" in p2["text"]

    # Verify duplicate detection on uploading same file again
    files_dup = {"file": ("research_paper.pdf", pdf_bytes, "application/pdf")}
    dup_res = client.post(f"/api/v1/workspaces/{workspace_id}/documents", files=files_dup)
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "DUPLICATE_DOCUMENT"

    # Delete document
    del_res = client.delete(f"/api/v1/workspaces/{workspace_id}/documents/{document_id}")
    assert del_res.status_code == 204

    # Verify deleted
    get_del_res = client.get(f"/api/v1/workspaces/{workspace_id}/documents/{document_id}")
    assert get_del_res.status_code == 404


def test_batch_upload_with_partial_rejection(client: TestClient):
    ws_res = client.post("/api/v1/workspaces", json={"name": "Batch Workspace"})
    workspace_id = ws_res.json()["id"]

    valid_pdf = create_sample_pdf(["Valid batch document content."])
    invalid_file = b"Just plain text file content."

    files = [
        ("files", ("valid.pdf", valid_pdf, "application/pdf")),
        ("files", ("notes.txt", invalid_file, "text/plain")),
    ]

    res = client.post(f"/api/v1/workspaces/{workspace_id}/documents/batch", files=files)
    assert res.status_code == 202
    data = res.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["filename"] == "valid.pdf"

    assert len(data["rejected"]) == 1
    assert data["rejected"][0]["filename"] == "notes.txt"
    assert data["rejected"][0]["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
