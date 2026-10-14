/**
 * ProofLens AI — Typed API Client for FastAPI Backend
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000/api/v1";

export interface Workspace {
  id: string;
  name: string;
  description?: string;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  workspace_id: string;
  filename?: string;
  original_filename?: string;
  content_type?: string;
  size_bytes: number;
  status: "queued" | "processing" | "ready" | "failed";
  page_count?: number;
  chunk_count?: number;
  error_message?: string;
  uploaded_at: string;
  processed_at?: string;
}

export interface DocumentPage {
  page_number: number;
  text?: string;
  text_content?: string;
  character_count?: number;
  extraction_status: string;
}

export interface CitationItem {
  chunk_id: string;
  document_id: string;
  page_numbers: number[];
  text_excerpt: string;
}

export interface SearchResultItem {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  text_content: string;
  page_numbers: number[];
  cosine_distance: number;
  cosine_similarity: number;
}

export interface SearchResponse {
  query: string;
  workspace_id: string;
  total_results: number;
  results: SearchResultItem[];
}

export interface AnalyseResponse {
  question: string;
  workspace_id: string;
  answer: string;
  citations: CitationItem[];
  model_used: string;
  chunks_used: number;
}

export interface DocumentFinding {
  document_id: string;
  document_name: string;
  key_points: string[];
  citations: CitationItem[];
}

export interface CompareResponse {
  workspace_id: string;
  topic: string;
  documents: DocumentFinding[];
  synthesis: string;
  relationship: "supports" | "differs" | "apparent_contradiction" | "not_comparable";
  model_used: string;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.error?.message) {
        errorDetail = errJson.error.message;
      } else if (errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Workspaces
  listWorkspaces: async (): Promise<Workspace[]> => {
    const res = await request<{ items: Workspace[] }>("/workspaces");
    return res.items || [];
  },

  createWorkspace: async (name: string, description?: string): Promise<Workspace> => {
    return request<Workspace>("/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    });
  },

  deleteWorkspace: async (workspaceId: string): Promise<void> => {
    await request<void>(`/workspaces/${workspaceId}`, { method: "DELETE" });
  },

  // Documents
  listDocuments: async (workspaceId: string): Promise<DocumentItem[]> => {
    const res = await request<{ items: DocumentItem[] }>(`/workspaces/${workspaceId}/documents`);
    return res.items || [];
  },

  uploadDocument: async (workspaceId: string, file: File): Promise<DocumentItem> => {
    const formData = new FormData();
    formData.append("file", file);
    return request<DocumentItem>(`/workspaces/${workspaceId}/documents`, {
      method: "POST",
      body: formData,
    });
  },

  getDocument: async (workspaceId: string, documentId: string): Promise<DocumentItem> => {
    return request<DocumentItem>(`/workspaces/${workspaceId}/documents/${documentId}`);
  },

  deleteDocument: async (workspaceId: string, documentId: string): Promise<void> => {
    await request<void>(`/workspaces/${workspaceId}/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  getPage: async (workspaceId: string, documentId: string, pageNumber: number): Promise<DocumentPage> => {
    return request<DocumentPage>(
      `/workspaces/${workspaceId}/documents/${documentId}/pages/${pageNumber}`
    );
  },

  // Semantic Search
  search: async (
    workspaceId: string,
    query: string,
    topK = 5
  ): Promise<SearchResponse> => {
    return request<SearchResponse>(`/workspaces/${workspaceId}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK }),
    });
  },

  // Grounded Analysis (QA)
  analyse: async (
    workspaceId: string,
    question: string,
    topK = 5
  ): Promise<AnalyseResponse> => {
    return request<AnalyseResponse>(`/workspaces/${workspaceId}/analyse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: topK }),
    });
  },

  // Cross-Document Comparison
  compare: async (
    workspaceId: string,
    documentIds: string[],
    topic: string,
    topKPerDoc = 3
  ): Promise<CompareResponse> => {
    return request<CompareResponse>(`/workspaces/${workspaceId}/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_ids: documentIds,
        topic,
        top_k_per_doc: topKPerDoc,
      }),
    });
  },
};
