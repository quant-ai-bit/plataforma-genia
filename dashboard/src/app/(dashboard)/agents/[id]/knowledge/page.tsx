"use client";

import React, { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "../../../../../lib/AppContext";
import { authenticatedFetch } from "../../../../../lib/api";
import { KbDocument } from "../../../../lib/types";
import {
  ArrowLeft,
  Bot,
  FileText,
  Upload,
  Plus,
  Trash2,
  Loader2,
  FolderOpen,
  X,
  Edit
} from "lucide-react";

export default function AgentKnowledgePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const {
    agents,
    isBackendOnline
  } = useAppContext();

  const [agent, setAgent] = useState<any>(null);

  // Documents list
  const [kbDocuments, setKbDocuments] = useState<KbDocument[]>([]);
  const [kbDocsLoading, setKbDocsLoading] = useState<boolean>(false);

  // Form states
  const [kbUploadMode, setKbUploadMode] = useState<"file" | "text">("file");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [manualTextTitle, setManualTextTitle] = useState<string>("");
  const [manualTextContent, setManualTextContent] = useState<string>("");
  const [isUploading, setIsUploading] = useState<boolean>(false);

  // Edit document states
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [editingDoc, setEditingDoc] = useState<KbDocument | null>(null);
  const [editTitle, setEditTitle] = useState<string>("");
  const [editContent, setEditContent] = useState<string>("");
  const [isLoadingDetails, setIsLoadingDetails] = useState<boolean>(false);
  const [isSavingEdit, setIsSavingEdit] = useState<boolean>(false);


  useEffect(() => {
    const foundAgent = agents.find(a => a.id === id);
    if (foundAgent) {
      setAgent(foundAgent);
    }
  }, [id, agents]);

  useEffect(() => {
    if (id) {
      loadKbDocuments();
    }
  }, [id, isBackendOnline]);

  const loadKbDocuments = async () => {
    setKbDocsLoading(true);
    if (!isBackendOnline) {
      // Mock documents
      setKbDocuments([
        { id: "doc-1", agent_id: id, filename: "faq_inmobiliario.txt", content_type: "text/plain", chunk_count: 5, uploaded_at: new Date().toISOString() },
        { id: "doc-2", agent_id: id, filename: "politica_precios.pdf", content_type: "application/pdf", chunk_count: 12, uploaded_at: new Date().toISOString() }
      ]);
      setKbDocsLoading(false);
      return;
    }
    try {
      const res = await authenticatedFetch(`/api/agents/${id}/documents`);
      if (res.ok) {
        const data = await res.json();
        setKbDocuments(data);
      }
    } catch (err) {
      console.error("Error al cargar documentos RAG:", err);
    } finally {
      setKbDocsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !id) return;
    setIsUploading(true);

    if (!isBackendOnline) {
      // Mock upload
      setTimeout(() => {
        const newDoc: KbDocument = {
          id: `doc-${Date.now()}`,
          agent_id: id,
          filename: uploadFile.name,
          content_type: uploadFile.type || "text/plain",
          chunk_count: Math.floor(Math.random() * 8) + 1,
          uploaded_at: new Date().toISOString()
        };
        setKbDocuments(prev => [newDoc, ...prev]);
        setUploadFile(null);
        setIsUploading(false);
      }, 1000);
      return;
    }

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);

      const res = await authenticatedFetch(`/api/agents/${id}/documents`, {
        method: "POST",
        body: formData
      });

      if (res.ok) {
        setUploadFile(null);
        await loadKbDocuments();
      } else {
        const data = await res.json();
        alert(`Error al subir: ${data.detail || "Archivo no soportado"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al subir el documento.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleManualTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualTextTitle.trim() || !manualTextContent.trim() || !id) return;
    setIsUploading(true);

    if (!isBackendOnline) {
      // Mock manual text
      setTimeout(() => {
        const newDoc: KbDocument = {
          id: `doc-${Date.now()}`,
          agent_id: id,
          filename: manualTextTitle.endsWith(".txt") ? manualTextTitle : `${manualTextTitle}.txt`,
          content_type: "text/plain",
          chunk_count: Math.floor(Math.random() * 5) + 1,
          uploaded_at: new Date().toISOString()
        };
        setKbDocuments(prev => [newDoc, ...prev]);
        setManualTextTitle("");
        setManualTextContent("");
        setIsUploading(false);
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/agents/${id}/documents/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: manualTextTitle,
          content: manualTextContent
        })
      });

      if (res.ok) {
        setManualTextTitle("");
        setManualTextContent("");
        await loadKbDocuments();
      } else {
        const data = await res.json();
        alert(`Error al guardar texto: ${data.detail || "Error desconocido"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al guardar el texto.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm("¿Deseas eliminar este documento del conocimiento del agente?")) return;

    if (!isBackendOnline) {
      setKbDocuments(prev => prev.filter(d => d.id !== docId));
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/documents/${docId}`, { method: "DELETE" });
      if (res.ok) {
        await loadKbDocuments();
      } else {
        alert("Error al eliminar el documento.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleOpenEditModal = async (doc: KbDocument) => {
    setEditingDoc(doc);
    setEditTitle(doc.filename.replace(/\.txt$/, ""));
    setEditContent("");
    setIsEditModalOpen(true);
    setIsLoadingDetails(true);

    if (!isBackendOnline) {
      setTimeout(() => {
        setEditContent("Este es un contenido de prueba del documento mock de conocimiento. Puedes editarlo aquí.");
        setIsLoadingDetails(false);
      }, 800);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/knowledge/documents/${doc.id}`);
      if (res.ok) {
        const data = await res.json();
        setEditContent(data.raw_content || "");
      } else {
        alert("No se pudo obtener el contenido del documento.");
        setIsEditModalOpen(false);
      }
    } catch (err) {
      console.error(err);
      alert("Error al conectar con el servidor.");
      setIsEditModalOpen(false);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingDoc || !editTitle.trim() || !editContent.trim()) return;
    setIsSavingEdit(true);

    if (!isBackendOnline) {
      setTimeout(() => {
        setKbDocuments(prev => prev.map(d => {
          if (d.id === editingDoc.id) {
            return {
              ...d,
              filename: editTitle.endsWith(".txt") ? editTitle : `${editTitle}.txt`,
              chunk_count: Math.floor(Math.random() * 5) + 2
            };
          }
          return d;
        }));
        setIsEditModalOpen(false);
        setEditingDoc(null);
        setIsSavingEdit(false);
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/knowledge/documents/${editingDoc.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editTitle,
          content: editContent
        })
      });

      if (res.ok) {
        setIsEditModalOpen(false);
        setEditingDoc(null);
        await loadKbDocuments();
      } else {
        const data = await res.json();
        alert(`Error al guardar cambios: ${data.detail || "Error desconocido"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error al conectar con el servidor al guardar.");
    } finally {
      setIsSavingEdit(false);
    }
  };


  if (!agent) {
    return (
      <div className="flex h-64 items-center justify-center text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-xs">Cargando base de conocimiento...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12 animate-fadeIn text-xs">
      
      {/* Back button */}
      <button
        onClick={() => router.push("/agents")}
        className="flex items-center gap-1 text-gray-400 hover:text-white transition font-semibold cursor-pointer mb-2"
      >
        <ArrowLeft className="w-4 h-4" />
        Volver a Agentes
      </button>

      {/* Title */}
      <div className="flex items-center gap-4 bg-gray-900/10 border border-gray-850 p-6 rounded-2xl">
        <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/15">
          <FileText className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <h3 className="text-md font-bold text-white">Base de Conocimiento RAG: {agent.name}</h3>
          <p className="text-xs text-gray-400 mt-0.5">Sube archivos o escribe texto para que el agente responda preguntas basándose en estos datos.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Upload Form Section (1 col) */}
        <div>
          <div className="glow-card p-5 rounded-2xl sticky top-8 space-y-4">
            <h4 className="text-xs font-bold text-white mb-2">Cargar Conocimiento</h4>
            
            {/* Mode selection buttons */}
            <div className="flex bg-[#0c101c] p-1 rounded-xl border border-gray-850">
              <button
                type="button"
                onClick={() => setKbUploadMode("file")}
                className={`flex-1 py-1.5 text-center text-[10px] font-bold rounded-lg transition-all cursor-pointer ${
                  kbUploadMode === "file"
                    ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Subir Archivo
              </button>
              <button
                type="button"
                onClick={() => setKbUploadMode("text")}
                className={`flex-1 py-1.5 text-center text-[10px] font-bold rounded-lg transition-all cursor-pointer ${
                  kbUploadMode === "text"
                    ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Texto Manual
              </button>
            </div>

            {/* File Upload Mode */}
            {kbUploadMode === "file" ? (
              <form onSubmit={handleFileUpload} className="space-y-4">
                <div className="relative border-2 border-dashed border-gray-850 hover:border-blue-500/30 rounded-xl p-6 flex flex-col items-center justify-center gap-2 cursor-pointer text-center hover:bg-blue-500/5 transition">
                  <input
                    type="file"
                    accept=".txt,.pdf,.docx,.doc"
                    onChange={e => {
                      if (e.target.files?.[0]) setUploadFile(e.target.files[0]);
                    }}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                  />
                  <Upload className="w-6 h-6 text-gray-500" />
                  <span className="text-[10px] text-gray-400 font-semibold truncate max-w-[150px]">
                    {uploadFile ? uploadFile.name : "Selecciona un Archivo"}
                  </span>
                  <span className="text-[8px] text-gray-550">TXT, PDF, DOCX (máx. 10MB)</span>
                </div>

                {uploadFile && (
                  <div className="flex items-center justify-between p-2 bg-[#0c101c] border border-gray-850 rounded-lg">
                    <span className="truncate max-w-[80%] text-gray-300 font-medium">{uploadFile.name}</span>
                    <button
                      type="button"
                      onClick={() => setUploadFile(null)}
                      className="text-gray-500 hover:text-red-400 cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!uploadFile || isUploading}
                  className="w-full flex items-center justify-center gap-1.5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold shadow-lg transition cursor-pointer"
                >
                  {isUploading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Subir y Procesar RAG
                    </>
                  )}
                </button>
              </form>
            ) : (
              /* Manual Text Mode */
              <form onSubmit={handleManualTextSubmit} className="space-y-4">
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Título del Documento</label>
                  <input
                    type="text"
                    required
                    placeholder="Ej. FAQ Horarios"
                    value={manualTextTitle}
                    onChange={e => setManualTextTitle(e.target.value)}
                    className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Contenido de Texto</label>
                  <textarea
                    required
                    rows={6}
                    placeholder="Escribe la información detallada aquí..."
                    value={manualTextContent}
                    onChange={e => setManualTextContent(e.target.value)}
                    className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none resize-none leading-relaxed"
                  />
                </div>
                <button
                  type="submit"
                  disabled={!manualTextTitle.trim() || !manualTextContent.trim() || isUploading}
                  className="w-full flex items-center justify-center gap-1.5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold shadow-lg transition cursor-pointer"
                >
                  {isUploading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      Guardar Texto en RAG
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>

        {/* Documents Gallery / List Section (2 cols) */}
        <div className="md:col-span-2 space-y-4">
          <h4 className="font-bold text-white text-xs">Documentos Cargados</h4>
          
          {kbDocsLoading ? (
            <div className="flex h-36 items-center justify-center">
              <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {kbDocuments.map((doc) => (
                <div key={doc.id} className="glow-card rounded-2xl p-5 flex flex-col justify-between bg-gray-900/10 border border-gray-850 space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg border border-blue-500/15 flex-shrink-0">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h5 className="font-bold text-gray-200 text-xs truncate" title={doc.filename}>
                        {doc.filename}
                      </h5>
                      <span className="text-[8px] font-mono px-1.5 py-0.5 bg-gray-850 text-gray-400 rounded border border-gray-700">
                        {doc.content_type.split("/")[1] || "text"}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between border-t border-gray-850/40 pt-3">
                    <div className="text-[9px] text-gray-500 font-semibold space-y-0.5">
                      <p>Fragmentos: {doc.chunk_count}</p>
                      <p>Subido: {new Date(doc.uploaded_at).toLocaleDateString()}</p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {doc.content_type === "text/plain" && (
                        <button
                          type="button"
                          onClick={() => handleOpenEditModal(doc)}
                          className="p-1.5 bg-blue-950/20 hover:bg-blue-900/30 text-blue-400 rounded-lg border border-blue-500/10 hover:border-blue-500/20 transition cursor-pointer"
                          title="Editar Documento"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleDeleteDocument(doc.id)}
                        className="p-1.5 bg-red-950/20 hover:bg-red-900/30 text-red-400 rounded-lg border border-red-500/10 hover:border-red-500/20 transition cursor-pointer"
                        title="Eliminar Documento"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {kbDocuments.length === 0 && (
                <div className="col-span-2 py-16 text-center text-gray-500 border border-dashed border-gray-850 rounded-2xl">
                  <FolderOpen className="w-8 h-8 mx-auto text-gray-600 mb-2" />
                  <p className="font-semibold text-xs">No hay documentos cargados en RAG</p>
                  <p className="text-[10px] text-gray-550 mt-0.5">Usa el formulario de la izquierda para dotar a tu agente de conocimiento contextual.</p>
                </div>
              )}
            </div>
          )}
        </div>

      </div>

      {/* Modal de Edición de Documento de Texto */}
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#0b0e17] border border-gray-850 rounded-2xl w-full max-w-2xl mx-4 overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-850 bg-gray-900/10">
              <div className="flex items-center gap-2">
                <Edit className="w-4 h-4 text-blue-400" />
                <h3 className="text-xs font-bold text-white">Editar Documento: {editingDoc?.filename}</h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingDoc(null);
                }}
                className="text-gray-400 hover:text-white cursor-pointer transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="p-6 space-y-4">
              {isLoadingDetails ? (
                <div className="flex flex-col items-center justify-center py-16 gap-3">
                  <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                  <p className="text-gray-400 text-[10px]">Cargando contenido del documento...</p>
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-gray-400 font-bold mb-1">Título del Documento</label>
                    <input
                      type="text"
                      required
                      placeholder="Ej. FAQ Horarios"
                      value={editTitle}
                      onChange={e => setEditTitle(e.target.value)}
                      className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white text-xs focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-400 font-bold mb-1">Contenido de Texto</label>
                    <textarea
                      required
                      rows={12}
                      placeholder="Escribe la información detallada aquí..."
                      value={editContent}
                      onChange={e => setEditContent(e.target.value)}
                      className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white text-xs focus:outline-none resize-none leading-relaxed"
                    />
                  </div>

                  <div className="flex justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        setIsEditModalOpen(false);
                        setEditingDoc(null);
                      }}
                      className="px-4 py-2 bg-gray-850 hover:bg-gray-800 text-gray-300 rounded-xl font-bold transition cursor-pointer"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={isSavingEdit || !editTitle.trim() || !editContent.trim()}
                      className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold shadow-lg transition cursor-pointer"
                    >
                      {isSavingEdit ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Guardando...
                        </>
                      ) : (
                        "Guardar Cambios"
                      )}
                    </button>
                  </div>
                </>
              )}
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

