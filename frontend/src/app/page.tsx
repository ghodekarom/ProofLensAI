"use client";

import { useEffect, useState, useCallback, useId } from "react";
import {
  FolderPlus,
  Trash2,
  FileText,
  Upload,
  Search,
  Sparkles,
  GitCompare,
  CheckCircle2,
  Clock,
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Layers,
  ShieldAlert,
} from "lucide-react";
import {
  api,
  Workspace,
  DocumentItem,
  AnalyseResponse,
  CompareResponse,
  DocumentPage,
} from "@/lib/api";

export default function ProofLensDashboard() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState(true);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);

  // Active view tab: "ask" | "compare" | "documents"
  const [activeTab, setActiveTab] = useState<"ask" | "compare" | "documents">("ask");

  // Document upload state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Page preview modal
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [previewPageNum, setPreviewPageNum] = useState<number>(1);
  const [pageContent, setPageContent] = useState<DocumentPage | null>(null);
  const [isLoadingPage, setIsLoadingPage] = useState(false);

  // Q&A State
  const [question, setQuestion] = useState("");
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalyseResponse | null>(null);

  // Comparison State
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [compareTopic, setCompareTopic] = useState("");
  const [isComparing, setIsComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState<CompareResponse | null>(null);

  const fileInputId = useId();

  // Load Workspaces manually
  const loadWorkspaces = useCallback(async () => {
    try {
      const list = await api.listWorkspaces();
      setWorkspaces(list);
    } catch (err: unknown) {
      console.error("Failed to load workspaces", err);
    }
  }, []);

  // Load Documents for active workspace
  const loadDocuments = useCallback(async () => {
    if (!activeWorkspace) return;
    try {
      const docs = await api.listDocuments(activeWorkspace.id);
      setDocuments(docs);
    } catch (err: unknown) {
      console.error("Failed to load documents", err);
    }
  }, [activeWorkspace]);

  // Initial load
  useEffect(() => {
    let ignore = false;
    api.listWorkspaces()
      .then((list) => {
        if (!ignore) {
          setWorkspaces(list);
          setIsLoadingWorkspaces(false);
          if (list.length > 0) {
            setActiveWorkspace((prev) => prev ?? list[0]);
          }
        }
      })
      .catch((err: unknown) => {
        console.error("Failed to load workspaces", err);
        if (!ignore) setIsLoadingWorkspaces(false);
      });
    return () => {
      ignore = true;
    };
  }, []);

  // Workspace selection handler
  const selectWorkspace = (ws: Workspace) => {
    setActiveWorkspace(ws);
    setAnalysisResult(null);
    setComparisonResult(null);
    setSelectedDocIds([]);
  };

  useEffect(() => {
    if (!activeWorkspace) return;
    let ignore = false;
    api.listDocuments(activeWorkspace.id)
      .then((docs) => {
        if (!ignore) {
          setDocuments(docs);
        }
      })
      .catch((err: unknown) => {
        console.error("Failed to load documents", err);
      });
    return () => {
      ignore = true;
    };
  }, [activeWorkspace]);

  // Poll for document processing status if any document is queued/processing
  useEffect(() => {
    const hasPending = documents.some(
      (d) => d.status === "queued" || d.status === "processing"
    );
    if (!hasPending) return;

    const interval = setInterval(() => {
      loadDocuments();
    }, 2000);

    return () => clearInterval(interval);
  }, [documents, loadDocuments]);

  // Create Workspace Handler
  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    try {
      setIsCreatingWorkspace(true);
      const created = await api.createWorkspace(newWorkspaceName.trim());
      setWorkspaces((prev) => [created, ...prev]);
      setActiveWorkspace(created);
      setNewWorkspaceName("");
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsCreatingWorkspace(false);
    }
  };

  // Delete Workspace Handler
  const handleDeleteWorkspace = async (id: string) => {
    if (!confirm("Are you sure you want to delete this workspace and all its indexed documents?")) return;
    try {
      await api.deleteWorkspace(id);
      const remaining = workspaces.filter((w) => w.id !== id);
      setWorkspaces(remaining);
      setActiveWorkspace(remaining[0] || null);
    } catch (err: unknown) {
      alert((err as Error).message);
    }
  };

  // Upload Document Handler
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !uploadFile) return;
    try {
      setIsUploading(true);
      setUploadError(null);
      await api.uploadDocument(activeWorkspace.id, uploadFile);
      setUploadFile(null);
      await loadDocuments();
    } catch (err: unknown) {
      setUploadError((err as Error).message);
    } finally {
      setIsUploading(false);
    }
  };

  // Delete Document Handler
  const handleDeleteDocument = async (docId: string) => {
    if (!activeWorkspace) return;
    if (!confirm("Delete this document and all its vector embeddings?")) return;
    try {
      await api.deleteDocument(activeWorkspace.id, docId);
      loadDocuments();
    } catch (err: unknown) {
      alert((err as Error).message);
    }
  };

  // Inspect Page Text Handler
  const handleInspectPage = async (doc: DocumentItem, pageNum: number) => {
    if (!activeWorkspace) return;
    setPreviewDoc(doc);
    setPreviewPageNum(pageNum);
    setIsLoadingPage(true);
    try {
      const page = await api.getPage(activeWorkspace.id, doc.id, pageNum);
      setPageContent(page);
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsLoadingPage(false);
    }
  };

  // Ask Question Handler
  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !question.trim()) return;
    try {
      setIsAnalysing(true);
      const res = await api.analyse(activeWorkspace.id, question.trim(), 5);
      setAnalysisResult(res);
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsAnalysing(false);
    }
  };

  // Compare Documents Handler
  const handleCompare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || selectedDocIds.length < 2 || !compareTopic.trim()) return;
    try {
      setIsComparing(true);
      const res = await api.compare(activeWorkspace.id, selectedDocIds, compareTopic.trim(), 3);
      setComparisonResult(res);
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsComparing(false);
    }
  };

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 antialiased overflow-hidden font-sans">
      {/* ── Left Sidebar: Workspaces & Navigation ─────────────────────────── */}
      <aside className="w-80 border-r border-zinc-800/80 bg-zinc-900/60 flex flex-col backdrop-blur-xl">
        {/* Brand Header */}
        <div className="p-5 border-b border-zinc-800/80 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Sparkles className="w-5 h-5 text-zinc-950" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
              ProofLens AI
            </h1>
            <p className="text-xs text-zinc-400 font-medium">Verifiable Document Intelligence</p>
          </div>
        </div>

        {/* Workspaces List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="flex items-center justify-between text-xs font-semibold tracking-wider text-zinc-400 uppercase">
            <span>Workspaces</span>
            <span>{workspaces.length}</span>
          </div>

          {/* New Workspace Input */}
          <form onSubmit={handleCreateWorkspace} className="flex gap-2">
            <input
              type="text"
              placeholder="New workspace..."
              value={newWorkspaceName}
              onChange={(e) => setNewWorkspaceName(e.target.value)}
              className="flex-1 bg-zinc-800/60 border border-zinc-700/60 rounded-lg px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
            />
            <button
              type="submit"
              disabled={isCreatingWorkspace || !newWorkspaceName.trim()}
              className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg px-2.5 py-1.5 text-xs font-medium transition disabled:opacity-40"
            >
              <FolderPlus className="w-4 h-4" />
            </button>
          </form>

          {/* List items */}
          <div className="space-y-1">
            {isLoadingWorkspaces ? (
              <div className="p-4 text-center text-xs text-zinc-500">Loading workspaces...</div>
            ) : workspaces.length === 0 ? (
              <div className="p-4 text-center text-xs text-zinc-500">No workspaces found. Create one above!</div>
            ) : (
              workspaces.map((ws) => {
                const isActive = activeWorkspace?.id === ws.id;
                return (
                  <div
                    key={ws.id}
                    onClick={() => selectWorkspace(ws)}
                    className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer text-xs transition border ${
                      isActive
                        ? "bg-indigo-950/40 border-indigo-500/40 text-white shadow-sm"
                        : "hover:bg-zinc-800/40 border-transparent text-zinc-400 hover:text-zinc-200"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 overflow-hidden">
                      <Layers className={`w-4 h-4 shrink-0 ${isActive ? "text-indigo-400" : "text-zinc-500"}`} />
                      <span className="truncate font-medium">{ws.name}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
                        {ws.document_count}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteWorkspace(ws.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 hover:text-red-400 p-1 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Workspace Info Footer */}
        {activeWorkspace && (
          <div className="p-4 border-t border-zinc-800/80 bg-zinc-950/40 text-[11px] text-zinc-400 flex items-center justify-between">
            <span className="truncate">Active: <strong className="text-zinc-200">{activeWorkspace.name}</strong></span>
            <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">Single User Demo</span>
          </div>
        )}
      </aside>

      {/* ── Main Content Area ─────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col bg-zinc-950 overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 border-b border-zinc-800/80 px-8 flex items-center justify-between bg-zinc-900/30 backdrop-blur-md">
          <div className="flex items-center gap-6">
            <nav className="flex space-x-1 bg-zinc-900/80 p-1 rounded-xl border border-zinc-800">
              <button
                onClick={() => setActiveTab("ask")}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-medium transition ${
                  activeTab === "ask"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Search className="w-3.5 h-3.5" />
                Ask & Grounded Citations
              </button>
              <button
                onClick={() => setActiveTab("compare")}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-medium transition ${
                  activeTab === "compare"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <GitCompare className="w-3.5 h-3.5" />
                Cross-Document Compare
              </button>
              <button
                onClick={() => setActiveTab("documents")}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-medium transition ${
                  activeTab === "documents"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                Documents ({documents.length})
              </button>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                loadWorkspaces();
                loadDocuments();
              }}
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 px-3 py-1.5 rounded-lg border border-zinc-800 hover:bg-zinc-800/60 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Sync
            </button>
          </div>
        </header>

        {/* Body Viewport */}
        <div className="flex-1 overflow-y-auto p-8">
          {!activeWorkspace ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <Layers className="w-12 h-12 text-zinc-600 mb-3" />
              <h3 className="text-lg font-semibold text-zinc-300">No Workspace Selected</h3>
              <p className="text-xs text-zinc-500 max-w-sm mt-1">
                Select or create a workspace on the sidebar to start uploading documents and performing grounded QA.
              </p>
            </div>
          ) : activeTab === "ask" ? (
            /* ── VIEW 1: Evidence-Grounded Q&A ─────────────────────────────── */
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Question Input Card */}
              <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 shadow-xl backdrop-blur-md">
                <form onSubmit={handleAsk} className="space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-2">
                      <Search className="w-4 h-4 text-indigo-400" />
                      Ask a Question Across Workspace Documents
                    </label>
                    <span className="text-[11px] text-zinc-500 font-medium">Model: Gemini 3.8 Flash</span>
                  </div>
                  <div className="relative">
                    <textarea
                      rows={3}
                      placeholder="e.g. What are the key findings regarding retrieval hit rates and evaluation benchmarks?"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      className="w-full bg-zinc-950/70 border border-zinc-800 rounded-xl p-4 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition resize-none"
                    />
                  </div>
                  <div className="flex justify-between items-center pt-2">
                    <span className="text-xs text-zinc-500">
                      Grounded on {documents.filter((d) => d.status === "ready").length} indexed PDF documents
                    </span>
                    <button
                      type="submit"
                      disabled={isAnalysing || !question.trim() || documents.length === 0}
                      className="bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-medium px-5 py-2.5 rounded-xl shadow-lg shadow-indigo-600/20 transition flex items-center gap-2 disabled:opacity-40"
                    >
                      {isAnalysing ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Retrieving & Analyzing...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5" />
                          Generate Grounded Answer
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>

              {/* Analysis Result Display */}
              {analysisResult && (
                <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 shadow-xl space-y-6">
                  <div>
                    <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-cyan-400" />
                      Grounded Answer
                    </h3>
                    <div className="prose prose-invert max-w-none text-sm text-zinc-200 leading-relaxed bg-zinc-950/50 p-5 rounded-xl border border-zinc-800/60 whitespace-pre-wrap">
                      {analysisResult.answer.replace(/\s*\[Page\s+[\d,\s]+\]/gi, "")}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : activeTab === "compare" ? (
            /* ── VIEW 2: Cross-Document Comparison ─────────────────────────── */
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 shadow-xl space-y-5">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                    <GitCompare className="w-4 h-4 text-indigo-400" />
                    Compare Findings Across Multiple Documents
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1">
                    Select at least 2 indexed documents to analyze agreements, differences, or contradictions.
                  </p>
                </div>

                {/* Document Selector Checkboxes */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                    Select Documents ({selectedDocIds.length} chosen):
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {documents.filter((d) => d.status === "ready").map((doc) => {
                      const isSelected = selectedDocIds.includes(doc.id);
                      return (
                        <div
                          key={doc.id}
                          onClick={() => {
                            setSelectedDocIds((prev) =>
                              isSelected ? prev.filter((id) => id !== doc.id) : [...prev, doc.id]
                            );
                          }}
                          className={`p-3 rounded-xl border cursor-pointer text-xs flex items-center justify-between transition ${
                            isSelected
                              ? "bg-indigo-950/40 border-indigo-500 text-white"
                              : "bg-zinc-950/40 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                          }`}
                        >
                          <div className="flex items-center gap-2 truncate">
                            <FileText className={`w-3.5 h-3.5 shrink-0 ${isSelected ? "text-indigo-400" : "text-zinc-500"}`} />
                            <span className="truncate">{doc.filename || doc.original_filename}</span>
                          </div>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            readOnly
                            className="rounded border-zinc-700 text-indigo-600 focus:ring-0"
                          />
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Topic Input */}
                <form onSubmit={handleCompare} className="space-y-4">
                  <div>
                    <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider block mb-1.5">
                      Comparison Topic / Criteria:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Retrieval accuracy, methodology, or benchmark outcomes"
                      value={compareTopic}
                      onChange={(e) => setCompareTopic(e.target.value)}
                      className="w-full bg-zinc-950/70 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
                    />
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={isComparing || selectedDocIds.length < 2 || !compareTopic.trim()}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-5 py-2.5 rounded-xl shadow-lg transition flex items-center gap-2 disabled:opacity-40"
                    >
                      {isComparing ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Synthesizing Comparison...
                        </>
                      ) : (
                        <>
                          <GitCompare className="w-3.5 h-3.5" />
                          Run Cross-Document Comparison
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>

              {/* Comparison Results Display */}
              {comparisonResult && (
                <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 shadow-xl space-y-6">
                  {/* Synthesis & Classification Banner */}
                  <div className="flex items-center justify-between p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                    <div>
                      <span className="text-[11px] text-zinc-400 uppercase tracking-wider font-semibold">
                        Relationship Finding:
                      </span>
                      <div className="text-sm font-bold text-zinc-100 capitalize mt-0.5">
                        {comparisonResult.relationship.replace("_", " ")}
                      </div>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                        comparisonResult.relationship === "supports"
                          ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/60"
                          : comparisonResult.relationship === "differs"
                          ? "bg-amber-950/60 text-amber-400 border border-amber-800/60"
                          : comparisonResult.relationship === "apparent_contradiction"
                          ? "bg-rose-950/60 text-rose-400 border border-rose-800/60"
                          : "bg-zinc-800 text-zinc-400"
                      }`}
                    >
                      {comparisonResult.relationship}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-2">Synthesis</h4>
                    <p className="text-xs text-zinc-200 leading-relaxed bg-zinc-950/50 p-4 rounded-xl border border-zinc-800/60 whitespace-pre-wrap">
                      {comparisonResult.synthesis}
                    </p>
                  </div>

                  {/* Per Document Findings */}
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Per-Document Evidence</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {comparisonResult.documents.map((finding) => (
                        <div
                          key={finding.document_id}
                          className="bg-zinc-950/60 border border-zinc-800/80 rounded-xl p-4 text-xs space-y-3"
                        >
                          <div className="font-semibold text-indigo-300 flex items-center gap-1.5 truncate">
                            <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                            <span className="truncate">{finding.document_name}</span>
                          </div>
                          <ul className="space-y-1.5 text-zinc-300 text-[11px]">
                            {finding.key_points.map((pt, i) => (
                              <li key={i} className="list-disc list-inside text-zinc-300">
                                {pt}
                              </li>
                            ))}
                          </ul>
                          {finding.citations.length > 0 && (
                            <div className="pt-2 border-t border-zinc-800 flex flex-wrap gap-1.5">
                              {finding.citations.map((c, i) => (
                                <span
                                  key={i}
                                  className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-700 text-[10px] text-zinc-300"
                                >
                                  Page {c.page_numbers.join(", ")}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* ── VIEW 3: Document Management ─────────────────────────────────── */
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Upload Card */}
              <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 shadow-xl space-y-4">
                <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                  <Upload className="w-4 h-4 text-indigo-400" />
                  Upload Technical PDF
                </h3>
                <form onSubmit={handleUpload} className="space-y-4">
                  <div className="border-2 border-dashed border-zinc-800 hover:border-zinc-700 rounded-xl p-6 text-center transition cursor-pointer">
                    <input
                      id={fileInputId}
                      type="file"
                      accept=".pdf"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                      className="hidden"
                    />
                    <label htmlFor={fileInputId} className="cursor-pointer">
                      <FileText className="w-8 h-8 text-zinc-500 mx-auto mb-2" />
                      <p className="text-xs text-zinc-300 font-medium">
                        {uploadFile ? uploadFile.name : "Click to select a PDF file (Max 25MB)"}
                      </p>
                      <p className="text-[11px] text-zinc-500 mt-1">Page text is extracted and vectorized with Gemini Embeddings</p>
                    </label>
                  </div>

                  {uploadError && (
                    <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 shrink-0" />
                      <span>{uploadError}</span>
                    </div>
                  )}

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={isUploading || !uploadFile}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-5 py-2.5 rounded-xl shadow-lg transition flex items-center gap-2 disabled:opacity-40"
                    >
                      {isUploading ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Uploading & Extracting...
                        </>
                      ) : (
                        <>
                          <Upload className="w-3.5 h-3.5" />
                          Upload PDF
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>

              {/* Document List Table */}
              <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl p-6 shadow-xl space-y-4">
                <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                  Indexed Documents in Workspace ({documents.length})
                </h4>
                {documents.length === 0 ? (
                  <div className="p-8 text-center text-xs text-zinc-500">No documents uploaded yet.</div>
                ) : (
                  <div className="divide-y divide-zinc-800/60">
                    {documents.map((doc) => (
                      <div key={doc.id} className="py-3.5 flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3 overflow-hidden">
                          <FileText className="w-5 h-5 text-indigo-400 shrink-0" />
                          <div className="truncate">
                            <p className="text-xs font-medium text-zinc-200 truncate">{doc.filename || doc.original_filename}</p>
                            <p className="text-[11px] text-zinc-500">
                              {(doc.size_bytes / 1024).toFixed(1)} KB • {doc.page_count ?? 0} pages • {doc.chunk_count ?? 0} chunks
                            </p>
                            {doc.status === "failed" && doc.error_message && (
                              <p className="text-[10px] text-rose-400 mt-0.5 max-w-md truncate" title={doc.error_message}>
                                {doc.error_message}
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-3 shrink-0">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-medium flex items-center gap-1 ${
                              doc.status === "ready"
                                ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/60"
                                : doc.status === "processing"
                                ? "bg-amber-950/60 text-amber-400 border border-amber-800/60 animate-pulse"
                                : doc.status === "failed"
                                ? "bg-rose-950/60 text-rose-400 border border-rose-800/60"
                                : "bg-zinc-800 text-zinc-400"
                            }`}
                          >
                            {doc.status === "ready" && <CheckCircle2 className="w-3 h-3" />}
                            {doc.status === "processing" && <Clock className="w-3 h-3" />}
                            {doc.status === "failed" && <AlertCircle className="w-3 h-3" />}
                            {doc.status}
                          </span>

                          {doc.status === "ready" && doc.page_count && doc.page_count > 0 && (
                            <button
                              onClick={() => handleInspectPage(doc, 1)}
                              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-800/60 hover:bg-zinc-800 transition"
                            >
                              <ExternalLink className="w-3 h-3" />
                              Inspect
                            </button>
                          )}

                          <button
                            onClick={() => handleDeleteDocument(doc.id)}
                            className="p-1.5 text-zinc-500 hover:text-rose-400 transition"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ── Page Inspection Modal ─────────────────────────────────────────── */}
      {previewDoc && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold text-zinc-200">{previewDoc.filename || previewDoc.original_filename}</h3>
                <p className="text-[11px] text-zinc-500">Page {previewPageNum} of {previewDoc.page_count || 1}</p>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="text-zinc-500 hover:text-zinc-200 text-xs px-2.5 py-1 rounded bg-zinc-800"
              >
                Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 text-xs text-zinc-200 font-mono leading-relaxed bg-zinc-950/70 whitespace-pre-wrap">
              {isLoadingPage ? "Loading page text..." : (pageContent?.text_content || pageContent?.text || "No extracted text on this page.")}
            </div>

            <div className="p-3 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-400">
              <button
                disabled={previewPageNum <= 1 || isLoadingPage}
                onClick={() => handleInspectPage(previewDoc, previewPageNum - 1)}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40"
              >
                Previous Page
              </button>
              <span>Characters: {pageContent?.character_count ?? (pageContent?.text_content?.length || pageContent?.text?.length || 0)}</span>
              <button
                disabled={previewPageNum >= (previewDoc.page_count || 1) || isLoadingPage}
                onClick={() => handleInspectPage(previewDoc, previewPageNum + 1)}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40"
              >
                Next Page
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
