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
  ShieldCheck,
  ShieldAlert,
  Copy,
  Check,
  Zap,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Plus,
  X,
  Menu,
} from "lucide-react";
import {
  api,
  Workspace,
  DocumentItem,
  AnalyseResponse,
  CompareResponse,
  DocumentPage,
} from "@/lib/api";

const SUGGESTED_PROMPTS = [
  "Which technologies are used for the CourseHub backend, frontend, and database?",
  "What are the core OOP concepts discussed in the document?",
  "What is the standard error response format and status code for validation failures?",
  "What are the course enrollment business rules?",
  "What Docker container requirements are mentioned?",
];

const COMPARISON_TOPICS = [
  "Architectural patterns and technology stack",
  "Error handling standards and status codes",
  "Security and authentication requirements",
  "Database schemas and persistence rules",
];

export default function ProofLensDashboard() {
  // Workspaces State
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState(true);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Documents State
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Active View Tab: "ask" | "compare" | "documents"
  const [activeTab, setActiveTab] = useState<"ask" | "compare" | "documents">("ask");

  // Q&A State
  const [question, setQuestion] = useState("");
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalyseResponse | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  // Comparison State
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [compareTopic, setCompareTopic] = useState("");
  const [isComparing, setIsComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState<CompareResponse | null>(null);

  // Page Inspection Modal State
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [previewPageNum, setPreviewPageNum] = useState<number>(1);
  const [pageContent, setPageContent] = useState<DocumentPage | null>(null);
  const [isLoadingPage, setIsLoadingPage] = useState(false);
  const [isPageTextCopied, setIsPageTextCopied] = useState(false);

  const fileInputId = useId();

  // Load Workspaces
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

  // Sync documents when active workspace changes
  useEffect(() => {
    if (!activeWorkspace) return;
    let ignore = false;
    api.listDocuments(activeWorkspace.id)
      .then((docs) => {
        if (!ignore) setDocuments(docs);
      })
      .catch((err: unknown) => console.error("Failed to load documents", err));
    return () => {
      ignore = true;
    };
  }, [activeWorkspace]);

  // Poll for document status if any are queued/processing
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

  // Switch workspace
  const selectWorkspace = (ws: Workspace) => {
    setActiveWorkspace(ws);
    setAnalysisResult(null);
    setComparisonResult(null);
    setSelectedDocIds([]);
  };

  // Create Workspace
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

  // Delete Workspace
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

  // Upload Document
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

  // Delete Document
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

  // Inspect Page Text
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

  // Ask Question
  const handleAsk = async (e: React.FormEvent, customQuestion?: string) => {
    if (e) e.preventDefault();
    const q = customQuestion || question;
    if (!activeWorkspace || !q.trim()) return;
    try {
      setIsAnalysing(true);
      const res = await api.analyse(activeWorkspace.id, q.trim(), 5);
      setAnalysisResult(res);
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsAnalysing(false);
    }
  };

  // Copy Answer
  const copyAnswer = () => {
    if (!analysisResult) return;
    const clean = analysisResult.answer.replace(/\s*\[Page\s+[\d,\s]+\]/gi, "");
    navigator.clipboard.writeText(clean);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  // Copy Page Text
  const copyPageText = () => {
    const text = pageContent?.text_content || pageContent?.text || "";
    if (!text) return;
    navigator.clipboard.writeText(text);
    setIsPageTextCopied(true);
    setTimeout(() => setIsPageTextCopied(false), 2000);
  };

  // Compare Documents
  const handleCompare = async (e: React.FormEvent, customTopic?: string) => {
    if (e) e.preventDefault();
    const t = customTopic || compareTopic;
    if (!activeWorkspace || selectedDocIds.length < 2 || !t.trim()) return;
    try {
      setIsComparing(true);
      const res = await api.compare(activeWorkspace.id, selectedDocIds, t.trim(), 3);
      setComparisonResult(res);
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsComparing(false);
    }
  };

  const readyDocuments = documents.filter((d) => d.status === "ready");

  return (
    <div className="flex h-screen bg-[#07090E] text-zinc-100 antialiased overflow-hidden font-sans relative selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* ── Atmospheric Ambient Lights ─────────────────────────────────────────── */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none -z-0" />
      <div className="absolute top-1/3 right-10 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none -z-0" />

      {/* ── Left Sidebar (Workspaces & Navigation) ─────────────────────────── */}
      <aside
        className={`${
          sidebarOpen ? "w-80" : "w-0 -translate-x-full"
        } transition-all duration-300 ease-in-out border-r border-white/[0.07] bg-[#0A0D14]/90 flex flex-col backdrop-blur-2xl z-20 overflow-hidden relative shrink-0`}
      >
        {/* Brand Header */}
        <div className="p-5 border-b border-white/[0.07] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-500 via-indigo-600 to-cyan-400 p-[1px] shadow-lg shadow-indigo-500/20">
              <div className="w-full h-full bg-[#0B0E17] rounded-[15px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-cyan-300" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-base tracking-tight bg-gradient-to-r from-white via-zinc-100 to-zinc-400 bg-clip-text text-transparent">
                  ProofLens AI
                </h1>
                <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  v1.0
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 font-medium">Grounded Document Intelligence</p>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden text-zinc-400 hover:text-zinc-200 p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Workspaces List Section */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="flex items-center justify-between text-[11px] font-semibold tracking-wider text-zinc-400 uppercase px-1">
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              Workspaces
            </span>
            <span className="px-2 py-0.5 rounded-md bg-white/[0.04] text-zinc-400 font-mono text-[10px]">
              {workspaces.length}
            </span>
          </div>

          {/* New Workspace Input */}
          <form onSubmit={handleCreateWorkspace} className="flex gap-2">
            <input
              type="text"
              placeholder="Create workspace..."
              value={newWorkspaceName}
              onChange={(e) => setNewWorkspaceName(e.target.value)}
              className="flex-1 bg-white/[0.03] border border-white/[0.08] rounded-xl px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500/60 focus:bg-white/[0.05] transition"
            />
            <button
              type="submit"
              disabled={isCreatingWorkspace || !newWorkspaceName.trim()}
              className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl px-3 py-2 text-xs font-medium transition disabled:opacity-30 shadow-md shadow-indigo-600/30 flex items-center justify-center shrink-0"
              title="Add Workspace"
            >
              <Plus className="w-4 h-4" />
            </button>
          </form>

          {/* List items */}
          <div className="space-y-1.5 pt-1">
            {isLoadingWorkspaces ? (
              <div className="p-6 text-center text-xs text-zinc-500 flex flex-col items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-zinc-600" />
                <span>Loading workspaces...</span>
              </div>
            ) : workspaces.length === 0 ? (
              <div className="p-6 text-center text-xs text-zinc-500 border border-dashed border-white/[0.06] rounded-xl">
                No workspaces found. Create one above to get started.
              </div>
            ) : (
              workspaces.map((ws) => {
                const isActive = activeWorkspace?.id === ws.id;
                return (
                  <div
                    key={ws.id}
                    onClick={() => selectWorkspace(ws)}
                    className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer text-xs transition duration-150 border ${
                      isActive
                        ? "bg-indigo-600/15 border-indigo-500/40 text-white shadow-sm glow-indigo"
                        : "hover:bg-white/[0.03] border-transparent text-zinc-400 hover:text-zinc-200"
                    }`}
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div
                        className={`w-2 h-2 rounded-full shrink-0 transition ${
                          isActive ? "bg-indigo-400 ring-4 ring-indigo-400/20" : "bg-zinc-700"
                        }`}
                      />
                      <span className="truncate font-medium">{ws.name}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-medium ${
                          isActive
                            ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                            : "bg-white/[0.04] text-zinc-500"
                        }`}
                      >
                        {ws.document_count} doc{ws.document_count === 1 ? "" : "s"}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteWorkspace(ws.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 hover:text-rose-400 p-1 transition rounded-lg hover:bg-rose-500/10"
                        title="Delete Workspace"
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

        {/* Engine Status & System Badge */}
        <div className="p-4 border-t border-white/[0.07] bg-[#07090F]/80 text-[11px] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-zinc-400 font-medium flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Engine Online
            </span>
            <span className="text-[10px] font-mono text-zinc-500">PostgreSQL + HNSW</span>
          </div>
          <div className="flex items-center justify-between text-zinc-500 text-[10px]">
            <span>Model: Gemini 3.5 Flash Lite</span>
            <span className="text-indigo-400">Low Latency</span>
          </div>
        </div>
      </aside>

      {/* ── Main Canvas ─────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col bg-[#07090E] overflow-hidden z-10">
        {/* Top Command Bar */}
        <header className="h-16 border-b border-white/[0.07] px-6 flex items-center justify-between bg-[#0A0D14]/70 backdrop-blur-xl shrink-0">
          <div className="flex items-center gap-4">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-zinc-300 transition"
                title="Open Sidebar"
              >
                <Menu className="w-4 h-4" />
              </button>
            )}

            {/* Segmented Navigation Tabs */}
            <nav className="flex space-x-1.5 bg-white/[0.03] p-1 rounded-2xl border border-white/[0.08]">
              <button
                onClick={() => setActiveTab("ask")}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition duration-150 ${
                  activeTab === "ask"
                    ? "bg-gradient-to-r from-indigo-600 to-indigo-500 text-white shadow-md shadow-indigo-600/25"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                Grounded Q&A
              </button>
              <button
                onClick={() => setActiveTab("compare")}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition duration-150 ${
                  activeTab === "compare"
                    ? "bg-gradient-to-r from-indigo-600 to-indigo-500 text-white shadow-md shadow-indigo-600/25"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]"
                }`}
              >
                <GitCompare className="w-3.5 h-3.5" />
                Cross-Document Compare
              </button>
              <button
                onClick={() => setActiveTab("documents")}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition duration-150 ${
                  activeTab === "documents"
                    ? "bg-gradient-to-r from-indigo-600 to-indigo-500 text-white shadow-md shadow-indigo-600/25"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]"
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                Document Vault
                <span className="px-1.5 py-0.2 rounded-full bg-white/[0.1] text-[10px] font-mono">
                  {documents.length}
                </span>
              </button>
            </nav>
          </div>

          {/* Right Header Status Controls */}
          <div className="flex items-center gap-3">
            {activeWorkspace && (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.07] text-xs">
                <span className="text-zinc-400">Workspace:</span>
                <span className="font-semibold text-zinc-200 truncate max-w-[140px]">
                  {activeWorkspace.name}
                </span>
              </div>
            )}
            <button
              onClick={() => {
                loadWorkspaces();
                loadDocuments();
              }}
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 px-3 py-2 rounded-xl border border-white/[0.08] hover:bg-white/[0.05] transition"
              title="Sync Workspaces & Documents"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Sync</span>
            </button>
          </div>
        </header>

        {/* Viewport Content */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8">
          {!activeWorkspace ? (
            /* Empty Workspace Prompt */
            <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto">
              <div className="w-16 h-16 rounded-3xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4 text-indigo-400 glow-indigo">
                <Layers className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-zinc-100">No Workspace Selected</h3>
              <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
                Select an existing workspace from the left sidebar or create a new workspace to start indexing PDFs and asking grounded questions.
              </p>
            </div>
          ) : activeTab === "ask" ? (
            /* ═══════════════════════════════════════════════════════════════════
               VIEW 1: Grounded Q&A (Flagship User Experience)
               ═══════════════════════════════════════════════════════════════════ */
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Question Input Capsule */}
              <div className="glass-panel-elevated rounded-3xl p-6 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/5 rounded-full blur-2xl pointer-events-none" />

                <form onSubmit={handleAsk} className="space-y-4 relative">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-cyan-400" />
                      Ask Any Question Across Workspace Documents
                    </label>
                    <span className="text-[11px] font-mono text-zinc-400 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                      Gemini 3.5 Flash Lite
                    </span>
                  </div>

                  <div className="relative">
                    <textarea
                      rows={3}
                      placeholder="e.g. Which technologies are used for the CourseHub backend, frontend, and database?"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      className="w-full bg-[#07090F]/80 border border-white/[0.08] rounded-2xl p-4 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition resize-none leading-relaxed"
                    />
                  </div>

                  {/* Suggested Quick Prompt Pills */}
                  <div className="space-y-2 pt-1">
                    <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1">
                      <Zap className="w-3 h-3 text-amber-400" /> Quick Prompts:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {SUGGESTED_PROMPTS.map((promptText, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => {
                            setQuestion(promptText);
                            handleAsk(undefined as unknown as React.FormEvent, promptText);
                          }}
                          className="text-[11px] px-3 py-1.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] text-zinc-300 hover:text-white transition text-left"
                        >
                          {promptText}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-3 border-t border-white/[0.06]">
                    <span className="text-xs text-zinc-400 flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                      Grounded on {readyDocuments.length} indexed document{readyDocuments.length === 1 ? "" : "s"}
                    </span>
                    <button
                      type="submit"
                      disabled={isAnalysing || !question.trim() || readyDocuments.length === 0}
                      className="bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white text-xs font-semibold px-6 py-2.5 rounded-xl shadow-lg shadow-indigo-600/25 transition flex items-center gap-2 disabled:opacity-30 disabled:pointer-events-none"
                    >
                      {isAnalysing ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Synthesizing Answer...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5" />
                          Generate Answer
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>

              {/* Analysis Result Card */}
              {analysisResult && (
                <div className="glass-panel-elevated rounded-3xl p-7 shadow-2xl space-y-4 border border-white/[0.09] glow-indigo transition duration-300">
                  <div className="flex items-center justify-between pb-3 border-b border-white/[0.07]">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                        <CheckCircle2 className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-wider">
                          Grounded Answer
                        </h3>
                        <p className="text-[10px] text-zinc-500 font-mono">
                          Generated via {analysisResult.model_used}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={copyAnswer}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-medium text-zinc-300 transition"
                        title="Copy answer"
                      >
                        {isCopied ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => setAnalysisResult(null)}
                        className="p-1.5 rounded-xl text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] transition"
                        title="Clear Answer"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="prose prose-invert max-w-none text-sm text-zinc-100 leading-relaxed bg-[#07090F]/70 p-6 rounded-2xl border border-white/[0.06] whitespace-pre-wrap font-sans">
                    {analysisResult.answer.replace(/\s*\[Page\s+[\d,\s]+\]/gi, "")}
                  </div>

                  <div className="flex items-center justify-between pt-2 text-[11px] text-zinc-500">
                    <span>Verified factual match across workspace corpus</span>
                    <span className="text-emerald-400/90 font-medium flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" /> Anti-Hallucination Guarded
                    </span>
                  </div>
                </div>
              )}
            </div>
          ) : activeTab === "compare" ? (
            /* ═══════════════════════════════════════════════════════════════════
               VIEW 2: Cross-Document Comparison
               ═══════════════════════════════════════════════════════════════════ */
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="glass-panel-elevated rounded-3xl p-6 shadow-2xl space-y-5">
                <div>
                  <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                    <GitCompare className="w-4 h-4 text-indigo-400" />
                    Cross-Document Comparative Analysis
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1">
                    Select at least 2 indexed documents to evaluate agreements, differences, or contradictions.
                  </p>
                </div>

                {/* Document Selector Checkboxes */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider block">
                    Choose Documents to Compare ({selectedDocIds.length} selected):
                  </label>
                  {readyDocuments.length === 0 ? (
                    <div className="p-4 rounded-xl border border-dashed border-white/[0.07] text-xs text-zinc-500 text-center">
                      Upload at least 2 documents in the Document Vault tab first.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                      {readyDocuments.map((doc) => {
                        const isSelected = selectedDocIds.includes(doc.id);
                        return (
                          <div
                            key={doc.id}
                            onClick={() => {
                              setSelectedDocIds((prev) =>
                                isSelected ? prev.filter((id) => id !== doc.id) : [...prev, doc.id]
                              );
                            }}
                            className={`p-3.5 rounded-2xl border cursor-pointer text-xs flex items-center justify-between transition ${
                              isSelected
                                ? "bg-indigo-600/20 border-indigo-500/60 text-white glow-indigo"
                                : "bg-white/[0.02] border-white/[0.06] text-zinc-400 hover:border-white/[0.12]"
                            }`}
                          >
                            <div className="flex items-center gap-2.5 overflow-hidden">
                              <FileText
                                className={`w-4 h-4 shrink-0 ${
                                  isSelected ? "text-indigo-400" : "text-zinc-500"
                                }`}
                              />
                              <span className="truncate font-medium">
                                {doc.filename || doc.original_filename}
                              </span>
                            </div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-white/[0.05] text-zinc-400 shrink-0">
                              {doc.page_count ?? 1} pgs
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Topic Input & Suggestions */}
                <form onSubmit={handleCompare} className="space-y-4 pt-2">
                  <div>
                    <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider block mb-1.5">
                      Comparison Topic / Criteria:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Architectural stack, security standards, or evaluation outcomes"
                      value={compareTopic}
                      onChange={(e) => setCompareTopic(e.target.value)}
                      className="w-full bg-[#07090F]/80 border border-white/[0.08] rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
                    />
                  </div>

                  {/* Suggestion Chips */}
                  <div className="flex flex-wrap gap-2">
                    {COMPARISON_TOPICS.map((topicItem, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          setCompareTopic(topicItem);
                          handleCompare(undefined as unknown as React.FormEvent, topicItem);
                        }}
                        className="text-[11px] px-3 py-1 rounded-lg bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.06] text-zinc-400 hover:text-zinc-200 transition"
                      >
                        {topicItem}
                      </button>
                    ))}
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      disabled={isComparing || selectedDocIds.length < 2 || !compareTopic.trim()}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-6 py-2.5 rounded-xl shadow-lg shadow-indigo-600/25 transition flex items-center gap-2 disabled:opacity-30 disabled:pointer-events-none"
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
                <div className="glass-panel-elevated rounded-3xl p-7 shadow-2xl space-y-6">
                  {/* Synthesis Banner */}
                  <div className="flex items-center justify-between p-4 rounded-2xl bg-[#07090F]/80 border border-white/[0.08]">
                    <div>
                      <span className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold">
                        Relationship Finding
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
                    <p className="text-xs text-zinc-200 leading-relaxed bg-[#07090F]/60 p-5 rounded-2xl border border-white/[0.06] whitespace-pre-wrap">
                      {comparisonResult.synthesis}
                    </p>
                  </div>

                  {/* Per Document Findings */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Per-Document Findings</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {comparisonResult.documents.map((finding) => (
                        <div
                          key={finding.document_id}
                          className="bg-[#07090F]/60 border border-white/[0.07] rounded-2xl p-4 text-xs space-y-2.5"
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
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* ═══════════════════════════════════════════════════════════════════
               VIEW 3: Document Vault & Ingestion
               ═══════════════════════════════════════════════════════════════════ */
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Upload Card */}
              <div className="glass-panel-elevated rounded-3xl p-6 shadow-2xl space-y-4">
                <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                  <Upload className="w-4 h-4 text-indigo-400" />
                  Upload Technical PDF Document
                </h3>
                <form onSubmit={handleUpload} className="space-y-4">
                  <div className="border-2 border-dashed border-white/[0.09] hover:border-indigo-500/50 rounded-2xl p-8 text-center transition cursor-pointer bg-white/[0.01] hover:bg-indigo-500/[0.02]">
                    <input
                      id={fileInputId}
                      type="file"
                      accept=".pdf"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                      className="hidden"
                    />
                    <label htmlFor={fileInputId} className="cursor-pointer block">
                      <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto mb-3">
                        <FileText className="w-6 h-6" />
                      </div>
                      <p className="text-xs text-zinc-200 font-semibold">
                        {uploadFile ? uploadFile.name : "Click to select or drop a PDF file (Max 25MB)"}
                      </p>
                      <p className="text-[11px] text-zinc-500 mt-1">
                        Page text will be extracted with PyMuPDF and vectorized with Gemini Embeddings
                      </p>
                    </label>
                  </div>

                  {uploadError && (
                    <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 shrink-0" />
                      <span>{uploadError}</span>
                    </div>
                  )}

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={isUploading || !uploadFile}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-6 py-2.5 rounded-xl shadow-lg shadow-indigo-600/25 transition flex items-center gap-2 disabled:opacity-30 disabled:pointer-events-none"
                    >
                      {isUploading ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Extracting & Vectorizing...
                        </>
                      ) : (
                        <>
                          <Upload className="w-3.5 h-3.5" />
                          Index Document
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>

              {/* Document Inventory Table */}
              <div className="glass-panel-elevated rounded-3xl p-6 shadow-2xl space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-cyan-400" />
                    Indexed Documents in Workspace ({documents.length})
                  </h4>
                  <span className="text-[11px] text-zinc-500 font-mono">pgvector HNSW</span>
                </div>

                {documents.length === 0 ? (
                  <div className="p-8 text-center text-xs text-zinc-500 border border-dashed border-white/[0.06] rounded-2xl">
                    No documents indexed yet in this workspace. Upload a PDF above to begin.
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.06]">
                    {documents.map((doc) => (
                      <div key={doc.id} className="py-4 flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3.5 overflow-hidden">
                          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
                            <FileText className="w-5 h-5" />
                          </div>
                          <div className="truncate">
                            <p className="text-xs font-semibold text-zinc-100 truncate">
                              {doc.filename || doc.original_filename}
                            </p>
                            <p className="text-[11px] text-zinc-400 mt-0.5 font-mono">
                              {(doc.size_bytes / 1024).toFixed(1)} KB • {doc.page_count ?? 0} pages • {doc.chunk_count ?? 0} chunks
                            </p>
                            {doc.status === "failed" && doc.error_message && (
                              <p className="text-[10px] text-rose-400 mt-1 max-w-md truncate" title={doc.error_message}>
                                {doc.error_message}
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-3 shrink-0">
                          <span
                            className={`px-2.5 py-1 rounded-full text-[10px] font-semibold flex items-center gap-1.5 uppercase tracking-wider ${
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
                              className="text-xs text-indigo-300 hover:text-white flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] transition"
                            >
                              <ExternalLink className="w-3 h-3" />
                              Inspect
                            </button>
                          )}

                          <button
                            onClick={() => handleDeleteDocument(doc.id)}
                            className="p-2 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition"
                            title="Delete Document"
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
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4 md:p-6">
          <div className="glass-panel-elevated rounded-3xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl border border-white/[0.12] overflow-hidden">
            <div className="p-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.02]">
              <div>
                <h3 className="text-xs font-bold text-zinc-100 truncate max-w-md">
                  {previewDoc.filename || previewDoc.original_filename}
                </h3>
                <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                  Page {previewPageNum} of {previewDoc.page_count || 1}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={copyPageText}
                  className="text-xs text-zinc-300 hover:text-white px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] transition flex items-center gap-1.5"
                >
                  {isPageTextCopied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => setPreviewDoc(null)}
                  className="text-zinc-400 hover:text-zinc-100 p-1.5 rounded-xl hover:bg-white/[0.08] transition"
                  title="Close Modal"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 text-xs text-zinc-200 font-mono leading-relaxed bg-[#07090F]/90 whitespace-pre-wrap select-text">
              {isLoadingPage
                ? "Extracting page content..."
                : (pageContent?.text_content || pageContent?.text || "No extracted text available on this page.")}
            </div>

            <div className="p-4 border-t border-white/[0.08] flex items-center justify-between text-xs text-zinc-400 bg-white/[0.02]">
              <button
                disabled={previewPageNum <= 1 || isLoadingPage}
                onClick={() => handleInspectPage(previewDoc, previewPageNum - 1)}
                className="px-3.5 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-zinc-200 disabled:opacity-30 transition flex items-center gap-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Previous
              </button>
              <span className="font-mono text-[11px] text-zinc-400">
                {pageContent?.character_count ?? (pageContent?.text_content?.length || pageContent?.text?.length || 0)} characters
              </span>
              <button
                disabled={previewPageNum >= (previewDoc.page_count || 1) || isLoadingPage}
                onClick={() => handleInspectPage(previewDoc, previewPageNum + 1)}
                className="px-3.5 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-zinc-200 disabled:opacity-30 transition flex items-center gap-1"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
