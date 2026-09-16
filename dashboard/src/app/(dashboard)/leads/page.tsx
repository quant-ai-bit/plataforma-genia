"use client";

import { useState, useMemo } from "react";
import { useAppContext } from "../../../lib/AppContext";
import { authenticatedFetch } from "../../../lib/api";
import { Lead } from "../../../lib/types";
import {
  UserCheck,
  Trash2,
  Eye,
  X,
  Mail,
  Phone,
  Calendar,
  Database,
  ExternalLink,
  Loader2,
  FolderOpen,
  Download,
  Upload,
  LayoutGrid,
  Table as TableIcon,
  MessageSquare,
  Sparkles,
  CheckCircle2,
  Clock,
  ChevronRight,
  Filter,
  Edit2,
  Plus,
  Check
} from "lucide-react";
import { useRouter } from "next/navigation";

// Definición dinámica de las etapas del Pipeline CRM
export interface PipelineStage {
  id: string;
  label: string;
  color: string;
  dot: string;
}

const DEFAULT_STAGES: PipelineStage[] = [
  { id: "primer_contacto", label: "Primer Contacto", color: "bg-blue-500/10 text-blue-400 border-blue-500/20", dot: "bg-blue-400" },
  { id: "en_cualificacion", label: "En Cualificación", color: "bg-amber-500/10 text-amber-400 border-amber-500/20", dot: "bg-amber-400" },
  { id: "cualificado", label: "Lead Cualificado", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", dot: "bg-emerald-400" },
  { id: "objetivo_cumplido", label: "Objetivo Cumplido", color: "bg-purple-500/10 text-purple-400 border-purple-500/20", dot: "bg-purple-400" },
  { id: "perdido", label: "Inactivo / Perdido", color: "bg-gray-500/10 text-gray-400 border-gray-500/20", dot: "bg-gray-400" },
];

export default function LeadsPage() {
  const router = useRouter();
  const {
    leads,
    agents,
    isBackendOnline,
    loadBackendData
  } = useAppContext();

  // Estados de vista y filtros
  const [viewMode, setViewMode] = useState<"pipeline" | "table">("pipeline");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [selectedAgentId, setSelectedAgentId] = useState<string>("all");
  const [selectedChannel, setSelectedChannel] = useState<string>("all");
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [statusUpdating, setStatusUpdating] = useState<string | null>(null);

  // Estados de etapas dinámicas y editables
  const [stages, setStages] = useState<PipelineStage[]>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("genia_crm_stages");
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          console.error("Error cargando etapas guardadas:", e);
        }
      }
    }
    return DEFAULT_STAGES;
  });

  const [editingStageId, setEditingStageId] = useState<string | null>(null);
  const [editingStageLabel, setEditingStageLabel] = useState<string>("");
  const [showAddStageModal, setShowAddStageModal] = useState<boolean>(false);
  const [newStageName, setNewStageName] = useState<string>("");

  const saveStages = (newStages: PipelineStage[]) => {
    setStages(newStages);
    if (typeof window !== "undefined") {
      localStorage.setItem("genia_crm_stages", JSON.stringify(newStages));
    }
  };

  const handleRenameStage = (id: string) => {
    if (!editingStageLabel.trim()) return;
    const updated = stages.map((s) => (s.id === id ? { ...s, label: editingStageLabel.trim() } : s));
    saveStages(updated);
    setEditingStageId(null);
    setEditingStageLabel("");
  };

  const handleAddStage = () => {
    if (!newStageName.trim()) return;
    const id = `stage_${Date.now()}`;
    const newStage: PipelineStage = {
      id,
      label: newStageName.trim(),
      color: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20",
      dot: "bg-indigo-400"
    };
    saveStages([...stages, newStage]);
    setNewStageName("");
    setShowAddStageModal(false);
  };

  const handleDeleteStage = (id: string) => {
    if (stages.length <= 1) {
      alert("Debes conservar al menos una etapa en el pipeline.");
      return;
    }
    if (confirm("¿Estás seguro de eliminar esta etapa del pipeline?")) {
      saveStages(stages.filter((s) => s.id !== id));
    }
  };

  // Estados del Modal de Carga Masiva CSV/Excel
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploadAgentId, setUploadAgentId] = useState<string>("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);

  // Cambio de estado en el Pipeline CRM
  const handleUpdateStatus = async (leadId: string, newStatus: string) => {
    setStatusUpdating(leadId);
    try {
      if (isBackendOnline) {
        const res = await authenticatedFetch(`/api/leads/${leadId}/status`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newStatus }),
        });
        if (res.ok) {
          await loadBackendData();
        } else {
          alert("Error al actualizar el estado del lead.");
        }
      }
    } catch (err) {
      console.error("Error cambiando estado de lead:", err);
    } finally {
      setStatusUpdating(null);
    }
  };

  // Eliminar lead
  const handleDeleteLead = async (leadId: string) => {
    if (!confirm("¿Estás seguro de eliminar este prospecto permanentemente?")) return;
    setDeleteLoading(leadId);

    if (!isBackendOnline) {
      alert("Lead eliminado localmente (Modo Demo)");
      setDeleteLoading(null);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/leads/${leadId}`, { method: "DELETE" });
      if (res.ok) {
        await loadBackendData();
        if (selectedLead?.id === leadId) setSelectedLead(null);
      } else {
        alert("Error al eliminar el prospecto.");
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al eliminar.");
    } finally {
      setDeleteLoading(null);
    }
  };

  // Carga masiva de contactos precargados CSV/Excel
  const handleUploadContacts = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadAgentId) {
      alert("Por favor selecciona un agente.");
      return;
    }
    if (!uploadFile) {
      alert("Por favor selecciona un archivo CSV o Excel.");
      return;
    }

    setUploading(true);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);

      const res = await authenticatedFetch(`/api/agents/${uploadAgentId}/contacts/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (res.ok) {
        setUploadResult(`✅ ${data.message || "Contactos cargados exitosamente."}`);
        setUploadFile(null);
        await loadBackendData();
      } else {
        setUploadResult(`❌ Error: ${data.detail || "No se pudo procesar el archivo."}`);
      }
    } catch (err) {
      console.error("Error al subir contactos:", err);
      setUploadResult("❌ Error de red o servidor al subir contactos.");
    } finally {
      setUploading(false);
    }
  };

  // Filtrado de leads
  const filteredLeads = useMemo(() => {
    return leads.filter((lead) => {
      const term = searchTerm.toLowerCase();
      const matchesSearch =
        (lead.name && lead.name.toLowerCase().includes(term)) ||
        (lead.email && lead.email.toLowerCase().includes(term)) ||
        (lead.phone && lead.phone.toLowerCase().includes(term)) ||
        (lead.agent_name && lead.agent_name.toLowerCase().includes(term));

      const matchesAgent = selectedAgentId === "all" || lead.agent_id === selectedAgentId;
      const matchesChannel = selectedChannel === "all" || lead.source_channel === selectedChannel;

      return matchesSearch && matchesAgent && matchesChannel;
    });
  }, [leads, searchTerm, selectedAgentId, selectedChannel]);

  // Extraer todas las claves únicas de custom_data para generar columnas dinámicas en la tabla
  const dynamicCustomKeys = useMemo(() => {
    const keysSet = new Set<string>();
    filteredLeads.forEach((l) => {
      if (l.custom_data && typeof l.custom_data === "object") {
        Object.keys(l.custom_data).forEach((k) => keysSet.add(k));
      }
    });
    return Array.from(keysSet);
  }, [filteredLeads]);

  // Exportar a Excel (.csv con BOM UTF-8 y delimitador ;)
  const exportToExcelCSV = () => {
    if (filteredLeads.length === 0) {
      alert("No hay leads para exportar.");
      return;
    }

    const headers = [
      "ID Lead",
      "Agente Asignado",
      "Nombre Cliente",
      "Teléfono WhatsApp",
      "Correo Electrónico",
      "Canal Origen",
      "Estado CRM",
      "Fecha Captura",
      ...dynamicCustomKeys.map((k) => `Campo: ${k}`),
    ];

    const rows = filteredLeads.map((l) => {
      const cleanPhone = (l.phone || "").replace(/\D/g, "");
      const customVals = dynamicCustomKeys.map((k) => {
        const val = l.custom_data?.[k];
        if (val === null || val === undefined) return "";
        return typeof val === "object" ? JSON.stringify(val).replace(/"/g, '""') : String(val).replace(/"/g, '""');
      });

      return [
        l.id || "",
        l.agent_name || "Agente Genia",
        (l.name || "Sin Nombre").replace(/"/g, '""'),
        cleanPhone ? `+${cleanPhone}` : "Sin teléfono",
        l.email || "Sin email",
        l.source_channel || "web",
        l.status || "primer_contacto",
        new Date(l.captured_at || l.created_at || "").toLocaleString(),
        ...customVals,
      ].map((cell) => `"${cell}"`).join(";");
    });

    const csvContent = "\uFEFF" + [headers.map((h) => `"${h}"`).join(";"), ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `Reporte_Leads_GENIA_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 animate-fadeIn text-xs">
      
      {/* Header Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-[#0c101c]/90 border border-gray-850 p-5 rounded-2xl glow-card">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/15">
            <UserCheck className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              Gestión de Prospectos & Pipeline CRM
              <span className="px-2 py-0.5 bg-purple-950/60 border border-purple-500/20 text-purple-300 text-[10px] rounded-full font-bold">
                {filteredLeads.length} leads
              </span>
            </h3>
            <p className="text-[11px] text-gray-400 mt-0.5">
              Visualiza el avance de tus prospectos desde el primer contacto hasta el cierre.
            </p>
          </div>
        </div>

        {/* Action Buttons: Import BD & Export Excel */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => {
              if (agents.length > 0 && !uploadAgentId) {
                setUploadAgentId(agents[0].id);
              }
              setShowUploadModal(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-bold border border-blue-500/20 shadow-lg transition cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5" />
            Importar BD Clientes (CSV/Excel)
          </button>

          <button
            onClick={exportToExcelCSV}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-300 rounded-xl font-bold border border-emerald-500/20 transition cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            Exportar Excel (.csv)
          </button>
        </div>
      </div>

      {/* Control Bar: Filters + View Mode Switcher */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-[#070b13]/80 border border-gray-850 p-3 rounded-xl">
        
        {/* Search & Filter dropdowns */}
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="relative flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Buscar por nombre, WhatsApp, email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-[#0c101c] border border-gray-800 focus:border-purple-500 rounded-xl px-3.5 py-2 text-white focus:outline-none placeholder:text-gray-600"
            />
          </div>

          {/* Filter Agent */}
          <div className="flex items-center gap-1.5 bg-[#0c101c] border border-gray-800 rounded-xl px-3 py-1.5">
            <Filter className="w-3.5 h-3.5 text-gray-500" />
            <select
              value={selectedAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              className="bg-transparent text-gray-300 text-xs focus:outline-none cursor-pointer"
            >
              <option value="all">Todos los Agentes</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Filter Channel */}
          <div className="flex items-center gap-1.5 bg-[#0c101c] border border-gray-800 rounded-xl px-3 py-1.5">
            <select
              value={selectedChannel}
              onChange={(e) => setSelectedChannel(e.target.value)}
              className="bg-transparent text-gray-300 text-xs focus:outline-none cursor-pointer"
            >
              <option value="all">Todos los Canales</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="web">Chat Web</option>
            </select>
          </div>
        </div>

        {/* View Mode Toggle: Pipeline CRM vs Tabla Excel */}
        <div className="flex items-center p-1 bg-[#0c101c] border border-gray-850 rounded-xl self-end md:self-auto">
          <button
            onClick={() => setViewMode("pipeline")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition ${
              viewMode === "pipeline"
                ? "bg-purple-600 text-white shadow"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            Pipeline CRM
          </button>
          <button
            onClick={() => setViewMode("table")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition ${
              viewMode === "table"
                ? "bg-purple-600 text-white shadow"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <TableIcon className="w-3.5 h-3.5" />
            Tabla Excel
          </button>
        </div>
      </div>

      {/* VISTA 1: PIPELINE CRM KANBAN */}
      {viewMode === "pipeline" && (
        <div className="flex gap-4 items-start overflow-x-auto pb-6">
          {stages.map((stage) => {
            const stageLeads = filteredLeads.filter(
              (l) => (l.status || "primer_contacto") === stage.id
            );

            return (
              <div
                key={stage.id}
                className="bg-[#0b0f19] border border-white/[0.08] rounded-2xl p-3 space-y-3 min-w-[280px] w-[280px] flex-shrink-0 min-h-[500px] flex flex-col"
              >
                {/* Column Header */}
                <div className={`flex items-center justify-between p-2.5 rounded-xl border ${stage.color}`}>
                  {editingStageId === stage.id ? (
                    <div className="flex items-center gap-1.5 flex-1 mr-1">
                      <input
                        type="text"
                        autoFocus
                        value={editingStageLabel}
                        onChange={(e) => setEditingStageLabel(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleRenameStage(stage.id);
                          if (e.key === "Escape") setEditingStageId(null);
                        }}
                        className="w-full bg-[#070a12] border border-white/20 rounded px-1.5 py-0.5 text-xs text-white focus:outline-none"
                      />
                      <button
                        onClick={() => handleRenameStage(stage.id)}
                        className="p-1 text-emerald-400 hover:text-emerald-300 cursor-pointer"
                        title="Guardar nombre"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 flex-1 group/header">
                      <span className={`w-2 h-2 rounded-full ${stage.dot}`} />
                      <span className="font-bold text-xs truncate max-w-[140px]">{stage.label}</span>
                      <button
                        onClick={() => {
                          setEditingStageId(stage.id);
                          setEditingStageLabel(stage.label);
                        }}
                        className="opacity-0 group-hover/header:opacity-100 p-0.5 text-slate-400 hover:text-white transition cursor-pointer"
                        title="Editar nombre de columna"
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                    </div>
                  )}

                  <div className="flex items-center gap-1">
                    <span className="px-2 py-0.5 bg-black/30 rounded-full font-bold text-[10px]">
                      {stageLeads.length}
                    </span>
                    {stages.length > 1 && (
                      <button
                        onClick={() => handleDeleteStage(stage.id)}
                        className="text-slate-500 hover:text-rose-400 p-0.5 text-[10px] cursor-pointer"
                        title="Eliminar columna"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Cards Container */}
                <div className="space-y-2.5 flex-1">
                  {stageLeads.map((lead) => {
                    const cleanPhone = (lead.phone || "").replace(/\D/g, "");
                    const isCustomEmpty = !lead.custom_data || Object.keys(lead.custom_data).length === 0;

                    return (
                      <div
                        key={lead.id}
                        className="bg-[#070b13] border border-white/[0.08] hover:border-indigo-500/40 p-3.5 rounded-xl space-y-3 transition-all shadow-md group relative"
                      >
                        {/* Agent & Channel Badge */}
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-indigo-300 font-bold bg-indigo-950/40 px-2 py-0.5 rounded-md border border-indigo-500/20 truncate max-w-[120px]">
                            {lead.agent_name || "Agente Genia"}
                          </span>
                          <span className={`px-2 py-0.5 rounded-md font-semibold uppercase ${
                            lead.source_channel === "whatsapp"
                              ? "bg-emerald-950/50 text-emerald-400 border border-emerald-500/15"
                              : "bg-blue-950/50 text-blue-400 border border-blue-500/15"
                          }`}>
                            {lead.source_channel || "web"}
                          </span>
                        </div>

                        {/* Customer Info */}
                        <div>
                          <h4 className="font-bold text-white text-xs truncate">
                            {lead.name || "Cliente Sin Nombre"}
                          </h4>
                          {cleanPhone ? (
                            <a
                              href={`https://wa.me/${cleanPhone}`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-emerald-400 hover:underline text-[11px] font-mono flex items-center gap-1 mt-0.5"
                            >
                              <MessageSquare className="w-3 h-3 text-emerald-400" />
                              +{cleanPhone}
                            </a>
                          ) : (
                            <span className="text-gray-500 italic text-[10px]">Sin teléfono</span>
                          )}
                        </div>

                        {/* Custom Data Badges */}
                        {!isCustomEmpty && (
                          <div className="flex flex-wrap gap-1 pt-1 border-t border-white/[0.06]">
                            {Object.entries(lead.custom_data || {}).slice(0, 3).map(([k, v]) => (
                              <span
                                key={k}
                                className="px-1.5 py-0.5 bg-gray-900 text-gray-300 border border-gray-800 rounded text-[9px] truncate max-w-[140px]"
                              >
                                <strong>{k}:</strong> {String(v)}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Stage Selector & Actions */}
                        <div className="flex items-center justify-between pt-2 border-t border-white/[0.06] text-[10px]">
                          <select
                            disabled={statusUpdating === lead.id}
                            value={lead.status || "primer_contacto"}
                            onChange={(e) => lead.id && handleUpdateStatus(lead.id, e.target.value)}
                            className="bg-[#0c101c] text-gray-300 border border-gray-800 focus:border-indigo-500 rounded px-1.5 py-1 focus:outline-none cursor-pointer"
                          >
                            {stages.map((s) => (
                              <option key={s.id} value={s.id}>
                                Move: {s.label}
                              </option>
                            ))}
                          </select>

                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => setSelectedLead(lead)}
                              className="p-1 hover:bg-gray-800 text-blue-400 rounded transition cursor-pointer"
                              title="Ver Ficha Completa"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => lead.id && handleDeleteLead(lead.id)}
                              className="p-1 hover:bg-gray-800 text-red-400 rounded transition cursor-pointer"
                              title="Eliminar Lead"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>

                      </div>
                    );
                  })}

                  {stageLeads.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-12 text-gray-600 border border-dashed border-white/[0.08] rounded-xl">
                      <FolderOpen className="w-5 h-5 mb-1 text-gray-650" />
                      <span className="text-[10px]">Sin prospectos</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Botón para agregar nueva etapa */}
          <div className="min-w-[220px] flex-shrink-0">
            <button
              onClick={() => setShowAddStageModal(true)}
              className="w-full py-4 px-4 rounded-2xl border border-dashed border-white/[0.15] hover:border-indigo-500/50 text-slate-400 hover:text-white bg-[#0b0f19]/40 hover:bg-[#0b0f19] flex items-center justify-center gap-2 text-xs font-semibold transition cursor-pointer"
            >
              <Plus className="w-4 h-4 text-indigo-400" />
              <span>+ Agregar Etapa</span>
            </button>
          </div>
        </div>
      )}

      {/* VISTA 2: TABLA ESTILO EXCEL PRO */}
      {viewMode === "table" && (
        <div className="glow-card rounded-2xl overflow-hidden border border-gray-850 bg-[#0c101c]/90">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 font-semibold uppercase bg-[#070b13]/90 text-[10px]">
                  <th className="px-4 py-3 border-r border-gray-850">Nombre Cliente</th>
                  <th className="px-4 py-3 border-r border-gray-850">Agente</th>
                  <th className="px-4 py-3 border-r border-gray-850">Teléfono WhatsApp</th>
                  <th className="px-4 py-3 border-r border-gray-850">Email</th>
                  <th className="px-4 py-3 border-r border-gray-850">Canal</th>
                  <th className="px-4 py-3 border-r border-gray-850">Estado CRM</th>

                  {/* Dynamic Custom Fields Columns */}
                  {dynamicCustomKeys.map((key) => (
                    <th key={key} className="px-4 py-3 border-r border-gray-850 text-purple-400 font-bold">
                      {key}
                    </th>
                  ))}

                  <th className="px-4 py-3 border-r border-gray-850">Fecha Captura</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-850/60 text-[11px]">
                {filteredLeads.map((lead) => {
                  const cleanPhone = (lead.phone || "").replace(/\D/g, "");
                  const stageObj = stages.find((s) => s.id === (lead.status || "primer_contacto"));

                  return (
                    <tr key={lead.id} className="hover:bg-gray-850/30 transition-colors">
                      {/* Name */}
                      <td className="px-4 py-3 font-bold text-gray-200 border-r border-gray-850/60">
                        {lead.name || <span className="text-gray-600 italic">No proporcionado</span>}
                      </td>

                      {/* Agent */}
                      <td className="px-4 py-3 text-purple-300 font-semibold border-r border-gray-850/60">
                        {lead.agent_name || "Agente Genia"}
                      </td>

                      {/* Phone */}
                      <td className="px-4 py-3 border-r border-gray-850/60 font-mono">
                        {cleanPhone ? (
                          <a
                            href={`https://wa.me/${cleanPhone}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-emerald-400 hover:underline flex items-center gap-1"
                          >
                            <MessageSquare className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                            +{cleanPhone}
                          </a>
                        ) : (
                          <span className="text-gray-600 italic">Sin teléfono</span>
                        )}
                      </td>

                      {/* Email */}
                      <td className="px-4 py-3 text-gray-300 border-r border-gray-850/60">
                        {lead.email || <span className="text-gray-600 italic">Sin email</span>}
                      </td>

                      {/* Channel */}
                      <td className="px-4 py-3 border-r border-gray-850/60">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          lead.source_channel === "whatsapp"
                            ? "bg-emerald-950/40 text-emerald-400 border border-emerald-500/20"
                            : "bg-blue-950/40 text-blue-400 border border-blue-500/20"
                        }`}>
                          {lead.source_channel || "web"}
                        </span>
                      </td>

                      {/* CRM Status */}
                      <td className="px-4 py-3 border-r border-gray-850/60">
                        <select
                          disabled={statusUpdating === lead.id}
                          value={lead.status || "primer_contacto"}
                          onChange={(e) => lead.id && handleUpdateStatus(lead.id, e.target.value)}
                          className="bg-[#070b13] text-gray-200 border border-gray-800 focus:border-purple-500 rounded px-2 py-1 text-[10px] focus:outline-none cursor-pointer"
                        >
                          {stages.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </td>

                      {/* Dynamic Custom Data Cells */}
                      {dynamicCustomKeys.map((key) => {
                        const val = lead.custom_data?.[key];
                        return (
                          <td key={key} className="px-4 py-3 text-gray-300 border-r border-gray-850/60">
                            {val !== undefined && val !== null ? (
                              <span className="px-2 py-0.5 bg-purple-950/30 text-purple-300 rounded border border-purple-500/10 text-[10px]">
                                {typeof val === "object" ? JSON.stringify(val) : String(val)}
                              </span>
                            ) : (
                              <span className="text-gray-700">-</span>
                            )}
                          </td>
                        );
                      })}

                      {/* Date Captured */}
                      <td className="px-4 py-3 text-gray-400 border-r border-gray-850/60 text-[10px]">
                        {new Date(lead.captured_at || lead.created_at || "").toLocaleString([], {
                          dateStyle: "short",
                          timeStyle: "short",
                        })}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-1.5">
                          <button
                            onClick={() => setSelectedLead(lead)}
                            className="p-1.5 bg-blue-950/30 hover:bg-blue-900/40 text-blue-400 rounded border border-blue-500/20"
                            title="Ver detalles"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            disabled={deleteLoading === lead.id}
                            onClick={() => lead.id && handleDeleteLead(lead.id)}
                            className="p-1.5 bg-red-950/30 hover:bg-red-900/40 text-red-400 rounded border border-red-500/20"
                            title="Eliminar lead"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}

                {filteredLeads.length === 0 && (
                  <tr>
                    <td colSpan={8 + dynamicCustomKeys.length} className="px-6 py-16 text-center text-gray-500">
                      <FolderOpen className="w-8 h-8 mx-auto text-gray-600 mb-2" />
                      <p className="font-semibold text-xs">No se encontraron prospectos</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* MODAL 1: CARGA MASIVA DE BASE DE DATOS DE CLIENTES (CSV / EXCEL) */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-[#070b13]/85 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn text-xs">
          <div className="glow-card max-w-md w-full rounded-2xl p-6 relative bg-[#0c101c] border border-gray-800 space-y-4">
            <button
              onClick={() => setShowUploadModal(false)}
              className="absolute top-4 right-4 p-1.5 hover:bg-gray-800 rounded-xl transition text-gray-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3 border-b border-gray-850 pb-3">
              <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/20">
                <Upload className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Importar BD de Clientes</h4>
                <p className="text-[10px] text-gray-400">Reconocimiento automático y saludo personalizado por nombre</p>
              </div>
            </div>

            <form onSubmit={handleUploadContacts} className="space-y-4">
              {/* Select Agent */}
              <div>
                <label className="block text-gray-300 font-bold mb-1">Seleccionar Agente Asignado</label>
                <select
                  value={uploadAgentId}
                  onChange={(e) => setUploadAgentId(e.target.value)}
                  className="w-full bg-[#070b13] border border-gray-800 focus:border-blue-500 rounded-xl p-2.5 text-white"
                  required
                >
                  <option value="">-- Elige un Agente --</option>
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.provider})
                    </option>
                  ))}
                </select>
              </div>

              {/* File Input */}
              <div>
                <label className="block text-gray-300 font-bold mb-1">Archivo de Contactos (.csv o .xlsx)</label>
                <input
                  type="file"
                  accept=".csv, .xlsx, .xls"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full bg-[#070b13] border border-gray-800 rounded-xl p-2 text-gray-300 text-xs focus:outline-none"
                  required
                />
                <p className="text-[10px] text-gray-500 mt-1">
                  💡 El archivo debe incluir columnas como: <code>nombre</code>, <code>telefono</code> (o WhatsApp), y <code>email</code>.
                </p>
              </div>

              {uploadResult && (
                <div className="p-3 bg-gray-900 border border-gray-800 rounded-xl text-[11px]">
                  {uploadResult}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="flex-1 py-2 bg-gray-900 text-gray-400 rounded-xl font-bold border border-gray-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold flex items-center justify-center gap-1.5 shadow-lg disabled:opacity-50"
                >
                  {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Subir e Importar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: DETALLE COMPLETO DEL LEAD */}
      {selectedLead && (
        <div className="fixed inset-0 bg-[#070b13]/85 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn text-xs">
          <div className="glow-card max-w-lg w-full rounded-2xl p-6 relative bg-[#0c101c] border border-gray-800 space-y-4">
            <button
              onClick={() => setSelectedLead(null)}
              className="absolute top-4 right-4 p-1.5 hover:bg-gray-800 rounded-xl transition text-gray-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3 border-b border-gray-850 pb-3">
              <div className="p-2.5 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/15">
                <UserCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">{selectedLead.name || "Cliente Sin Nombre"}</h4>
                <p className="text-[10px] text-gray-400">Agente: {selectedLead.agent_name || "Agente Genia"}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-2.5 bg-[#070b13] border border-gray-850 rounded-xl">
                <span className="text-[9px] text-gray-500 block">Teléfono WhatsApp</span>
                <span className="text-emerald-400 font-bold block truncate">{selectedLead.phone || "No especificado"}</span>
              </div>
              <div className="p-2.5 bg-[#070b13] border border-gray-850 rounded-xl">
                <span className="text-[9px] text-gray-500 block">Correo Electrónico</span>
                <span className="text-gray-250 font-bold block truncate">{selectedLead.email || "No especificado"}</span>
              </div>
            </div>

            {/* Custom Data List */}
            <div className="space-y-1.5">
              <span className="text-[10px] text-gray-400 font-bold uppercase block">Campos Calificados Extra</span>
              <div className="bg-[#070b13] border border-gray-850 rounded-xl p-3 space-y-2">
                {selectedLead.custom_data && Object.keys(selectedLead.custom_data).length > 0 ? (
                  Object.entries(selectedLead.custom_data).map(([k, v]) => (
                    <div key={k} className="flex justify-between items-center border-b border-gray-850 pb-1.5 last:border-b-0">
                      <span className="font-bold text-purple-300">{k}</span>
                      <span className="text-white font-semibold">{String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span className="text-gray-500 italic block text-center py-2">Sin datos adicionales</span>
                )}
              </div>
            </div>

            {/* Chat button */}
            {selectedLead.conversation_id && (
              <button
                onClick={() => {
                  setSelectedLead(null);
                  router.push(`/conversations?id=${selectedLead.conversation_id}`);
                }}
                className="w-full py-2 bg-gray-850 hover:bg-gray-800 text-gray-300 rounded-xl font-bold flex items-center justify-center gap-1.5 border border-gray-700 transition"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Ver Conversación de Origen
              </button>
            )}

            <div className="pt-2">
              <button
                onClick={() => setSelectedLead(null)}
                className="w-full py-2 bg-gray-900 text-gray-400 rounded-xl font-bold border border-gray-800 cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Agregar Nueva Etapa al Pipeline */}
      {showAddStageModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-indigo-400" /> Nueva Etapa del Pipeline
              </h3>
              <button
                onClick={() => setShowAddStageModal(false)}
                className="text-slate-400 hover:text-white text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-200 mb-1.5">
                  Nombre de la Nueva Columna
                </label>
                <input
                  type="text"
                  autoFocus
                  placeholder="Ej: Visita Agendada / Oferta Presentada / En Espera"
                  value={newStageName}
                  onChange={(e) => setNewStageName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleAddStage();
                  }}
                  className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.08]">
              <button
                onClick={() => setShowAddStageModal(false)}
                className="px-3.5 py-1.5 text-xs text-slate-400 hover:text-white cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddStage}
                className="px-4 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-xs font-semibold rounded-xl cursor-pointer"
              >
                Agregar Columna
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
