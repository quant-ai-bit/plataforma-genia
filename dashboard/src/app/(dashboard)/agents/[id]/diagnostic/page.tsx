"use client";

import { useState, useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { authenticatedFetch } from "../../../../../lib/api";
import { useAppContext } from "../../../../../lib/AppContext";
import {
  BusinessContext,
  WhatsAppContact,
  DiagnosticResult,
  DiagnosticStatus,
} from "../../../../../lib/types";
import {
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  Building2,
  CheckCircle2,
  AlertTriangle,
  Users,
  Filter,
  Play,
  Loader2,
  Clock,
  Send,
  Download,
  Kanban,
  Edit3,
  Search,
  CheckSquare,
  Square,
  Lock,
  ChevronRight,
  Info,
  UserCheck,
  Briefcase,
  UserCheck2,
  Tag,
  MessageSquare,
  Bot,
  RefreshCw,
  X,
} from "lucide-react";

export default function AgentDiagnosticPage() {
  const params = useParams();
  const router = useRouter();
  const agentId = params?.id as string;
  const { isBackendOnline, agents } = useAppContext();

  const currentAgent = useMemo(() => {
    return agents.find((a) => a.id === agentId);
  }, [agents, agentId]);

  // ── ESTADOS DEL FORMULARIO DE CONTEXTO DE NEGOCIO ──
  const [bContext, setBContext] = useState<BusinessContext>({
    business_name: "",
    business_type: "",
    products_services: "",
    ideal_client: "",
    sale_keywords: [],
    personal_keywords: [],
    additional_notes: "",
  });
  const [contextSaved, setContextSaved] = useState<boolean>(false);
  const [savingContext, setSavingContext] = useState<boolean>(false);
  const [editingContext, setEditingContext] = useState<boolean>(true);

  // ── ESTADOS DE PRIVACIDAD Y FILTROS ──
  const [acceptedPrivacy, setAcceptedPrivacy] = useState<boolean>(false);
  const [analysisMode, setAnalysisMode] = useState<"manual" | "auto">("manual");
  const [chatLimit, setChatLimit] = useState<number>(50);
  const [daysBack, setDaysBack] = useState<number>(30);

  // ── ESTADOS DE CONTACTOS DE WHATSAPP (MODO MANUAL) ──
  const [contacts, setContacts] = useState<WhatsAppContact[]>([]);
  const [loadingContacts, setLoadingContacts] = useState<boolean>(false);
  const [selectedChatIds, setSelectedChatIds] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>("");

  // ── ESTADOS DE DIAGNÓSTICO Y PROGRESO ──
  const [diagnosticStatus, setDiagnosticStatus] = useState<DiagnosticStatus>({
    status: "idle",
    progress: 0,
    current_chat: "Listo para iniciar",
    total_chats: 0,
    analyzed_chats: 0,
    estimated_remaining_seconds: 0,
    results: [],
  });
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<string>("all");

  // ── ESTADOS DE IMPORTACIÓN Y PIPELINE ──
  const [importing, setImporting] = useState<boolean>(false);
  const [sendingPipeline, setSendingPipeline] = useState<boolean>(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // ── ESTADOS DEL MODAL OUTBOUND (SEGUIMIENTO 1 A 1) ──
  const [selectedResultForOutbound, setSelectedResultForOutbound] = useState<DiagnosticResult | null>(null);
  const [outboundMessage, setOutboundMessage] = useState<string>("");
  const [customInstruction, setCustomInstruction] = useState<string>("");
  const [generatingSuggest, setGeneratingSuggest] = useState<boolean>(false);
  const [sendingOutbound, setSendingOutbound] = useState<boolean>(false);

  // ── CARGAR CONTEXTO EXISTENTE AL INICIAR ──
  useEffect(() => {
    if (agentId && isBackendOnline) {
      loadContext();
      loadDiagnosticStatus();
    }
  }, [agentId, isBackendOnline]);

  const loadContext = async () => {
    try {
      const res = await authenticatedFetch(`/api/agents/${agentId}/diagnostic/context`);
      if (res.ok) {
        const data = await res.json();
        if (data.context && data.context.business_name) {
          setBContext({
            business_name: data.context.business_name || "",
            business_type: data.context.business_type || "",
            products_services: data.context.products_services || "",
            ideal_client: data.context.ideal_client || "",
            sale_keywords: data.context.sale_keywords || [],
            personal_keywords: data.context.personal_keywords || [],
            additional_notes: data.context.additional_notes || "",
          });
          setContextSaved(true);
          setEditingContext(false);
        }
      }
    } catch (e) {
      console.error("Error cargando contexto:", e);
    }
  };

  const loadDiagnosticStatus = async () => {
    try {
      const res = await authenticatedFetch(`/api/agents/${agentId}/diagnostic/status`);
      if (res.ok) {
        const data = await res.json();
        setDiagnosticStatus(data);
        if (data.status === "running") {
          setIsRunning(true);
        }
      }
    } catch (e) {
      console.error("Error cargando estado:", e);
    }
  };

  // Guardar contexto de negocio (2 campos requeridos)
  const handleSaveContext = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bContext.business_name.trim() || !bContext.business_type.trim()) {
      alert("Por favor completa los dos campos obligatorios: Nombre del negocio y Tipo de negocio.");
      return;
    }
    setSavingContext(true);
    try {
      const res = await authenticatedFetch(`/api/agents/${agentId}/diagnostic/context`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bContext),
      });
      if (res.ok) {
        setContextSaved(true);
        setEditingContext(false);
      } else {
        alert("Error al guardar el contexto del negocio.");
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión con el backend.");
    } finally {
      setSavingContext(false);
    }
  };

  // Cargar contactos de WhatsApp (Modo Manual)
  const handleFetchContacts = async () => {
    setLoadingContacts(true);
    try {
      const res = await authenticatedFetch(
        `/api/agents/${agentId}/whatsapp/contacts?limit=${chatLimit}&days=${daysBack}`
      );
      if (res.ok) {
        const data = await res.json();
        setContacts(data.contacts || []);
      } else {
        alert("Error al obtener los contactos de WhatsApp.");
      }
    } catch (e) {
      console.error(e);
      alert("No se pudo conectar con el servidor para obtener contactos.");
    } finally {
      setLoadingContacts(false);
    }
  };

  // Iniciar Diagnóstico
  const handleStartDiagnostic = async () => {
    if (!acceptedPrivacy) {
      alert("Por favor acepta el aviso de privacidad para continuar con el diagnóstico.");
      return;
    }
    if (analysisMode === "manual" && selectedChatIds.length === 0) {
      alert("Por favor selecciona al menos 1 contacto en la lista o cambia al Modo Automático.");
      return;
    }

    setIsRunning(true);
    try {
      const payload = {
        selected_chat_ids: analysisMode === "manual" ? selectedChatIds : null,
        limit: chatLimit,
        days_back: daysBack,
      };

      const res = await authenticatedFetch(`/api/agents/${agentId}/diagnostic/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        setDiagnosticStatus(data.diagnostic_state);

        // Iniciar polling de estado cada 2 segundos
        const interval = setInterval(async () => {
          const statusRes = await authenticatedFetch(`/api/agents/${agentId}/diagnostic/status`);
          if (statusRes.ok) {
            const stData: DiagnosticStatus = await statusRes.json();
            setDiagnosticStatus(stData);
            if (stData.status === "completed" || stData.status === "failed") {
              clearInterval(interval);
              setIsRunning(false);
            }
          }
        }, 2000);
      } else {
        alert("Error al iniciar el diagnóstico.");
        setIsRunning(false);
      }
    } catch (e) {
      console.error(e);
      alert("Error al iniciar el diagnóstico.");
      setIsRunning(false);
    }
  };

  // Importar contactos analizados
  const handleImportContacts = async () => {
    if (!diagnosticStatus.results || diagnosticStatus.results.length === 0) return;
    setImporting(true);
    try {
      const res = await authenticatedFetch(`/api/agents/${agentId}/diagnostic/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ results: diagnosticStatus.results }),
      });
      if (res.ok) {
        const data = await res.json();
        setActionNotice(`✅ Importación exitosa: ${data.created} contactos creados y ${data.updated} actualizados.`);
      } else {
        alert("Error al importar contactos.");
      }
    } catch (e) {
      console.error(e);
      alert("Error en la importación.");
    } finally {
      setImporting(false);
    }
  };

  // Enviar leads al CRM
  const handleSendToPipeline = async () => {
    if (!diagnosticStatus.results || diagnosticStatus.results.length === 0) return;
    setSendingPipeline(true);
    try {
      const res = await authenticatedFetch(`/api/agents/${agentId}/diagnostic/pipeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ results: diagnosticStatus.results }),
      });
      if (res.ok) {
        const data = await res.json();
        setActionNotice(`🎯 CRM Actualizado: ${data.created_leads} leads creados y ${data.updated_leads} actualizados en el Kanban.`);
      } else {
        alert("Error al enviar leads al CRM.");
      }
    } catch (e) {
      console.error(e);
      alert("Error al enviar al CRM.");
    } finally {
      setSendingPipeline(false);
    }
  };

  // Sugerir mensaje con IA para el modal Outbound
  const handleSuggestOutbound = async () => {
    if (!selectedResultForOutbound) return;
    setGeneratingSuggest(true);
    try {
      const res = await authenticatedFetch(`/api/agents/${agentId}/outbound/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: selectedResultForOutbound.contact.phone,
          custom_instruction: customInstruction,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setOutboundMessage(data.suggested_message);
      } else {
        alert("Error generando sugerencia.");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingSuggest(false);
    }
  };

  // Enviar mensaje Outbound 1 a 1
  const handleSendOutbound = async () => {
    if (!selectedResultForOutbound || !outboundMessage.trim()) return;
    setSendingOutbound(true);
    try {
      const res = await authenticatedFetch(`/api/agents/${agentId}/outbound/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: selectedResultForOutbound.contact.phone,
          message: outboundMessage,
        }),
      });
      if (res.ok) {
        alert(`📲 Mensaje de seguimiento enviado exitosamente a +${selectedResultForOutbound.contact.phone}`);
        setSelectedResultForOutbound(null);
        setOutboundMessage("");
      } else {
        const errData = await res.json();
        alert(`Atención: ${errData.detail || "No se pudo enviar el mensaje."}`);
      }
    } catch (e) {
      console.error(e);
      alert("Error enviando mensaje.");
    } finally {
      setSendingOutbound(false);
    }
  };

  // Filtrado de contactos para tabla manual
  const filteredContacts = useMemo(() => {
    if (!searchTerm.trim()) return contacts;
    const term = searchTerm.toLowerCase();
    return contacts.filter(
      (c) =>
        c.name.toLowerCase().includes(term) ||
        c.phone.toLowerCase().includes(term) ||
        c.last_message.toLowerCase().includes(term)
    );
  }, [contacts, searchTerm]);

  // Selección de contactos en masa
  const handleSelectAllContacts = () => {
    if (selectedChatIds.length === filteredContacts.length) {
      setSelectedChatIds([]);
    } else {
      setSelectedChatIds(filteredContacts.map((c) => c.chat_id));
    }
  };

  // Filtrado de resultados por categoría
  const filteredResults = useMemo(() => {
    const list = diagnosticStatus.results || [];
    if (activeCategoryFilter === "all") return list;
    return list.filter((r) => r.category === activeCategoryFilter);
  }, [diagnosticStatus.results, activeCategoryFilter]);

  // Mapeo visual de categorías
  const CATEGORY_MAP: Record<string, { label: string; color: string; dot: string; icon: string }> = {
    cliente_potencial: { label: "Cliente Potencial", color: "bg-blue-500/10 text-blue-400 border-blue-500/30", dot: "bg-blue-400", icon: "🏢" },
    cliente_existente: { label: "Cliente Existente", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30", dot: "bg-emerald-400", icon: "✅" },
    aliado_estrategico: { label: "Aliado Estratégico", color: "bg-purple-500/10 text-purple-400 border-purple-500/30", dot: "bg-purple-400", icon: "🤝" },
    personal: { label: "Personal (Familia/Amigos)", color: "bg-pink-500/10 text-pink-400 border-pink-500/30", dot: "bg-pink-400", icon: "👥" },
    proveedor: { label: "Proveedor / Servicio", color: "bg-amber-500/10 text-amber-400 border-amber-500/30", dot: "bg-amber-400", icon: "📦" },
    irrelevante: { label: "Spam / Irrelevante", color: "bg-gray-500/10 text-gray-400 border-gray-500/30", dot: "bg-gray-400", icon: "🚫" },
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-white p-4 sm:p-6 md:p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* ── HEADER Y NAVEGACIÓN ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-800">
        <div>
          <button
            onClick={() => router.push(`/agents/${agentId}`)}
            className="inline-flex items-center gap-2 text-xs font-semibold text-gray-400 hover:text-purple-400 transition mb-3 cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            Volver a la configuración del agente
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-lg shadow-purple-950/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-white via-purple-100 to-purple-400 bg-clip-text text-transparent">
                Diagnóstico WhatsApp + CRM IA
              </h1>
              <p className="text-xs text-gray-400">
                Agente: <span className="text-purple-300 font-semibold">{currentAgent?.name || "Cargando..."}</span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Escaneo de Lectura Segura
          </span>
        </div>
      </div>

      {/* ── NOTIFICACIÓN DE ACCIONES ── */}
      {actionNotice && (
        <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-200 text-xs flex items-center justify-between">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-purple-400 hover:text-white cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ── SECCIÓN 1: FORMULARIO CONTEXTO DE NEGOCIO (EDITABLE) ── */}
      <div className="bg-[#0b101d] border border-gray-800 rounded-2xl p-5 sm:p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-gray-800/80 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Building2 className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
                1. Contexto de Negocio
                <span className="text-[10px] font-normal text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
                  2 Campos Obligatorios
                </span>
              </h2>
              <p className="text-xs text-gray-400">
                La IA usa esta información para clasificar correctamente clientes y detectar oportunidades comerciales.
              </p>
            </div>
          </div>

          {contextSaved && !editingContext && (
            <button
              type="button"
              onClick={() => setEditingContext(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-purple-500/30 bg-purple-500/10 text-purple-300 text-xs hover:bg-purple-500/20 transition cursor-pointer"
            >
              <Edit3 className="w-3.5 h-3.5" />
              Editar Contexto
            </button>
          )}
        </div>

        {contextSaved && !editingContext ? (
          <div className="bg-emerald-500/[0.03] border border-emerald-500/20 rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              Contexto de Negocio Activo y Listo para el Análisis IA
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-gray-400 block text-[11px]">Negocio:</span>
                <span className="text-white font-medium">{bContext.business_name}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[11px]">Tipo / Industria:</span>
                <span className="text-white font-medium">{bContext.business_type}</span>
              </div>
              {bContext.products_services && (
                <div className="md:col-span-2">
                  <span className="text-gray-400 block text-[11px]">Productos / Servicios:</span>
                  <span className="text-gray-300">{bContext.products_services}</span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSaveContext} className="space-y-4">
            {/* OBLIGATORIO 1 y 2 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Nombre del Negocio / Empresa <span className="text-red-400">* (Obligatorio)</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej: Legaria Capital / Inmobiliaria Pereira"
                  value={bContext.business_name}
                  onChange={(e) => setBContext({ ...bContext, business_name: e.target.value })}
                  className="w-full bg-[#121829] border border-gray-750 focus:border-purple-500 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Tipo de Negocio / Industria <span className="text-red-400">* (Obligatorio)</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej: Alquiler de Oficinas y Coworking"
                  value={bContext.business_type}
                  onChange={(e) => setBContext({ ...bContext, business_type: e.target.value })}
                  className="w-full bg-[#121829] border border-gray-750 focus:border-purple-500 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none transition"
                />
              </div>
            </div>

            {/* OPCIONALES 3 al 7 */}
            <div className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">
                  Productos / Servicios principales <span className="text-gray-500">(Opcional)</span>
                </label>
                <textarea
                  rows={2}
                  placeholder="Ej: Oficinas privadas amobladas, salas de junta por horas, puestos fijos de coworking..."
                  value={bContext.products_services}
                  onChange={(e) => setBContext({ ...bContext, products_services: e.target.value })}
                  className="w-full bg-[#121829] border border-gray-800 focus:border-purple-500 rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">
                  Perfil de Cliente Ideal / Comprador <span className="text-gray-500">(Opcional)</span>
                </label>
                <input
                  type="text"
                  placeholder="Ej: Emprendedores, independientes, empresas pequeñas de 2 a 10 personas..."
                  value={bContext.ideal_client}
                  onChange={(e) => setBContext({ ...bContext, ideal_client: e.target.value })}
                  className="w-full bg-[#121829] border border-gray-800 focus:border-purple-500 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">
                  Notas Adicionales de Contexto <span className="text-gray-500">(Opcional)</span>
                </label>
                <input
                  type="text"
                  placeholder="Ej: Contamos con sedes en Pinares, Pereira Plaza y Dosquebradas..."
                  value={bContext.additional_notes}
                  onChange={(e) => setBContext({ ...bContext, additional_notes: e.target.value })}
                  className="w-full bg-[#121829] border border-gray-800 focus:border-purple-500 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none transition"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={savingContext}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold transition cursor-pointer disabled:opacity-50"
              >
                {savingContext ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                Guardar Contexto de Negocio
              </button>
            </div>
          </form>
        )}
      </div>

      {/* ── SECCIÓN 2: AVISO LEGAL Y PRIVACIDAD ── */}
      <div className="bg-[#0c1222] border border-blue-500/20 rounded-2xl p-5 space-y-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0 mt-0.5">
            <Lock className="w-4 h-4" />
          </div>
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-blue-300">Garantía de Privacidad y Lectura Segura</h3>
            <p className="text-xs text-gray-300 leading-relaxed">
              🔒 <strong>Tus datos son privados y solo tuyos.</strong> La información de tu WhatsApp es procesada de forma
              estrictamente confidencial y <strong>únicamente visible para ti</strong> dentro de tu consola. El diagnóstico es una
              <strong>lectura pasiva del store local</strong> (equivalente a abrir WhatsApp Web) y no realiza envíos automáticos sin tu aprobación.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2 border-t border-gray-800/80">
          <label className="flex items-center gap-2 text-xs text-gray-200 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={acceptedPrivacy}
              onChange={(e) => setAcceptedPrivacy(e.target.checked)}
              className="w-4 h-4 rounded border-gray-700 bg-gray-900 text-purple-600 focus:ring-purple-500"
            />
            <span>He leído y acepto la política de diagnóstico y privacidad de datos.</span>
          </label>
        </div>
      </div>

      {/* ── SECCIÓN 3: CONFIGURACIÓN DE FILTROS Y ANÁLISIS ── */}
      <div className="bg-[#0b101d] border border-gray-800 rounded-2xl p-5 sm:p-6 space-y-6">
        <div className="flex items-center gap-3 border-b border-gray-800/80 pb-4">
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <Filter className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm sm:text-base font-bold text-white">2. Configurar Filtros y Modo de Diagnóstico</h2>
            <p className="text-xs text-gray-400">Elige los parámetros de tiempo y cantidad de chats para el análisis.</p>
          </div>
        </div>

        {/* MODO MANUAL VS AUTOMÁTICO */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => setAnalysisMode("manual")}
            className={`p-4 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between ${
              analysisMode === "manual"
                ? "bg-purple-500/10 border-purple-500/50 text-white"
                : "bg-[#121829] border-gray-800 text-gray-400 hover:border-gray-700"
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold flex items-center gap-2">
                  <CheckSquare className="w-4 h-4 text-purple-400" />
                  Modo Manual (Seleccionar Contactos)
                </span>
              </div>
              <p className="text-[11px] text-gray-400">
                Visualiza la lista de contactos de WhatsApp y elige exactamente cuáles chats analizar con la IA.
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => setAnalysisMode("auto")}
            className={`p-4 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between ${
              analysisMode === "auto"
                ? "bg-purple-500/10 border-purple-500/50 text-white"
                : "bg-[#121829] border-gray-800 text-gray-400 hover:border-gray-700"
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  Modo Automático (Filtro por Cantidad / Tiempo)
                </span>
              </div>
              <p className="text-[11px] text-gray-400">
                La IA escanea automáticamente los chats recientes según el límite de cantidad y rango de días.
              </p>
            </div>
          </button>
        </div>

        {/* SLIDERS DE FILTRO */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 bg-[#0e1424] p-4 rounded-xl border border-gray-800">
          <div>
            <div className="flex justify-between items-center mb-2 text-xs">
              <span className="font-semibold text-gray-300">Límite de Chats:</span>
              <span className="font-mono text-purple-400 font-bold">{chatLimit} chats</span>
            </div>
            <input
              type="range"
              min={10}
              max={200}
              step={10}
              value={chatLimit}
              onChange={(e) => setChatLimit(Number(e.target.value))}
              className="w-full accent-purple-500 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2 text-xs">
              <span className="font-semibold text-gray-300">Rango de Días:</span>
              <span className="font-mono text-purple-400 font-bold">Últimos {daysBack} días</span>
            </div>
            <input
              type="range"
              min={7}
              max={180}
              step={7}
              value={daysBack}
              onChange={(e) => setDaysBack(Number(e.target.value))}
              className="w-full accent-purple-500 cursor-pointer"
            />
          </div>
        </div>

        {/* LISTA DE CONTACTOS PARA MODO MANUAL */}
        {analysisMode === "manual" && (
          <div className="space-y-3 pt-2">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <button
                type="button"
                onClick={handleFetchContacts}
                disabled={loadingContacts}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition cursor-pointer disabled:opacity-50"
              >
                {loadingContacts ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                Cargar / Actualizar Lista de Contactos
              </button>

              {contacts.length > 0 && (
                <div className="flex items-center gap-3">
                  <div className="relative flex-1 sm:w-64">
                    <Search className="w-3.5 h-3.5 text-gray-500 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="Buscar por nombre o teléfono..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full bg-[#121829] border border-gray-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white focus:outline-none"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleSelectAllContacts}
                    className="text-xs text-purple-400 hover:underline cursor-pointer font-medium"
                  >
                    {selectedChatIds.length === filteredContacts.length ? "Desmarcar Todos" : "Seleccionar Todos"}
                  </button>
                </div>
              )}
            </div>

            {contacts.length > 0 && (
              <div className="border border-gray-800 rounded-xl overflow-hidden max-h-80 overflow-y-auto bg-[#070b14]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#101627] text-gray-400 font-semibold border-b border-gray-800 sticky top-0">
                    <tr>
                      <th className="p-3 w-10">#</th>
                      <th className="p-3">Contacto</th>
                      <th className="p-3">Último Mensaje</th>
                      <th className="p-3">Fecha</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60">
                    {filteredContacts.map((c) => {
                      const isSelected = selectedChatIds.includes(c.chat_id);
                      return (
                        <tr
                          key={c.chat_id}
                          onClick={() => {
                            if (isSelected) {
                              setSelectedChatIds(selectedChatIds.filter((id) => id !== c.chat_id));
                            } else {
                              setSelectedChatIds([...selectedChatIds, c.chat_id]);
                            }
                          }}
                          className={`cursor-pointer transition ${
                            isSelected ? "bg-purple-500/10" : "hover:bg-gray-800/30"
                          }`}
                        >
                          <td className="p-3">
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-purple-400" />
                            ) : (
                              <Square className="w-4 h-4 text-gray-600" />
                            )}
                          </td>
                          <td className="p-3 font-semibold text-white">
                            <div>{c.name}</div>
                            <div className="text-[10px] text-gray-500 font-mono">+{c.phone}</div>
                          </td>
                          <td className="p-3 text-gray-300 truncate max-w-xs">{c.last_message || "Sin preview"}</td>
                          <td className="p-3 text-gray-500 text-[11px]">
                            {new Date(c.last_message_at).toLocaleDateString("es-CO")}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* BOTÓN PRINCIPAL INICIAR DIAGNÓSTICO */}
        <div className="flex justify-end pt-3 border-t border-gray-800">
          <button
            type="button"
            disabled={isRunning || !acceptedPrivacy}
            onClick={handleStartDiagnostic}
            className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-purple-950/40 transition cursor-pointer disabled:opacity-50"
          >
            {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {isRunning ? "Ejecutando Diagnóstico IA..." : "Iniciar Diagnóstico WhatsApp"}
          </button>
        </div>
      </div>

      {/* ── SECCIÓN 4: PROGRESO Y ESTADO DEL DIAGNÓSTICO ── */}
      {isRunning && (
        <div className="bg-[#0b101d] border border-purple-500/30 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-purple-300 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
              {diagnosticStatus.current_chat}
            </span>
            <span className="font-mono text-purple-400 font-bold">{diagnosticStatus.progress}%</span>
          </div>

          {/* Barra de progreso */}
          <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-purple-500 to-indigo-400 h-full transition-all duration-500 rounded-full"
              style={{ width: `${diagnosticStatus.progress}%` }}
            ></div>
          </div>

          <div className="flex justify-between items-center text-[11px] text-gray-400">
            <span>
              Procesados: {diagnosticStatus.analyzed_chats} / {diagnosticStatus.total_chats} chats
            </span>
            <span className="flex items-center gap-1 font-mono">
              <Clock className="w-3 h-3 text-purple-400" />
              Tiempo estimado restante: ~{diagnosticStatus.estimated_remaining_seconds}s
            </span>
          </div>
        </div>
      )}

      {/* ── SECCIÓN 5: RESULTADOS Y ACCIONES POR CATEGORÍA ── */}
      {diagnosticStatus.results && diagnosticStatus.results.length > 0 && (
        <div className="bg-[#0b101d] border border-gray-800 rounded-2xl p-5 sm:p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-4">
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                3. Resultados del Diagnóstico IA
                <span className="text-xs font-normal text-purple-300 bg-purple-500/10 border border-purple-500/20 px-2.5 py-0.5 rounded-full">
                  {diagnosticStatus.results.length} Chats Categorizados
                </span>
              </h2>
              <p className="text-xs text-gray-400">
                Contactos clasificados por IA con detección de apodos y contexto comercial.
              </p>
            </div>

            {/* BOTONES GLOBALES PIPELINE E IMPORTACIÓN */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={importing}
                onClick={handleImportContacts}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-300 hover:bg-blue-600/30 text-xs font-semibold transition cursor-pointer disabled:opacity-50"
              >
                {importing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                Importar Contactos
              </button>

              <button
                type="button"
                disabled={sendingPipeline}
                onClick={handleSendToPipeline}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition cursor-pointer shadow-lg shadow-emerald-950/30 disabled:opacity-50"
              >
                {sendingPipeline ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Kanban className="w-3.5 h-3.5" />}
                Enviar al Pipeline CRM Kanban
              </button>
            </div>
          </div>

          {/* FILTROS POR CATEGORÍA */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
            <button
              onClick={() => setActiveCategoryFilter("all")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
                activeCategoryFilter === "all"
                  ? "bg-purple-600 text-white"
                  : "bg-[#121829] text-gray-400 hover:text-white border border-gray-800"
              }`}
            >
              Todos ({diagnosticStatus.results.length})
            </button>
            {Object.keys(CATEGORY_MAP).map((catKey) => {
              const count = (diagnosticStatus.results || []).filter((r) => r.category === catKey).length;
              if (count === 0) return null;
              const info = CATEGORY_MAP[catKey];
              return (
                <button
                  key={catKey}
                  onClick={() => setActiveCategoryFilter(catKey)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer border ${
                    activeCategoryFilter === catKey
                      ? info.color + " font-bold"
                      : "bg-[#121829] text-gray-400 hover:text-white border-gray-800"
                  }`}
                >
                  {info.icon} {info.label} ({count})
                </button>
              );
            })}
          </div>

          {/* LISTA DE TARJETAS RESULTADO */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredResults.map((resItem, idx) => {
              const catInfo = CATEGORY_MAP[resItem.category] || CATEGORY_MAP.irrelevante;
              return (
                <div
                  key={idx}
                  className="bg-[#0e1424] border border-gray-800 hover:border-gray-700 rounded-xl p-4 space-y-3 transition flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    {/* Header Card */}
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                          {resItem.contact.name}
                          {resItem.nickname && (
                            <span className="text-[11px] font-normal text-purple-300 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded-md">
                              Apodo: "{resItem.nickname}"
                            </span>
                          )}
                        </h3>
                        <span className="text-[10px] text-gray-500 font-mono">+{resItem.contact.phone}</span>
                      </div>

                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-semibold border ${catInfo.color}`}>
                        {catInfo.icon} {catInfo.label}
                      </span>
                    </div>

                    {/* Explicación IA */}
                    <p className="text-xs text-gray-300 leading-relaxed bg-[#070b14] p-2.5 rounded-lg border border-gray-850">
                      "{resItem.reason}"
                    </p>

                    {/* Datos comerciales si existen */}
                    {resItem.business_data && (resItem.business_data.interest || resItem.business_data.budget) && (
                      <div className="text-[11px] text-amber-300/90 bg-amber-500/[0.04] p-2 rounded-lg border border-amber-500/20 space-y-1">
                        {resItem.business_data.interest && <div>💡 Interés: {resItem.business_data.interest}</div>}
                        {resItem.business_data.budget && <div>💰 Presupuesto: {resItem.business_data.budget}</div>}
                      </div>
                    )}
                  </div>

                  {/* Acciones de Tarjeta */}
                  <div className="flex items-center justify-between pt-3 border-t border-gray-800/80 text-[11px]">
                    <span className="text-gray-500">
                      Confianza IA: <strong className="text-gray-300">{Math.round(resItem.confidence * 100)}%</strong>
                    </span>

                    <button
                      type="button"
                      onClick={() => {
                        setSelectedResultForOutbound(resItem);
                        setOutboundMessage("");
                        setCustomInstruction("");
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 font-medium transition cursor-pointer"
                    >
                      <Send className="w-3 h-3 text-purple-400" />
                      Seguimiento Outbound (1 a 1)
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── MODAL OUTBOUND SEGUIMIENTO 1 A 1 ── */}
      {selectedResultForOutbound && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0d1322] border border-purple-500/30 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2 text-purple-300 font-bold text-sm">
                <Send className="w-4 h-4 text-purple-400" />
                Seguimiento Outbound 1 a 1 (WhatsApp)
              </div>
              <button
                onClick={() => setSelectedResultForOutbound(null)}
                className="text-gray-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs space-y-2">
              <div className="bg-[#121829] p-3 rounded-xl border border-gray-800 flex justify-between items-center">
                <div>
                  <span className="text-gray-400 block text-[10px]">Destinatario:</span>
                  <span className="text-white font-bold">{selectedResultForOutbound.contact.name}</span>
                  {selectedResultForOutbound.nickname && (
                    <span className="text-purple-300 text-[11px] ml-2">("{selectedResultForOutbound.nickname}")</span>
                  )}
                </div>
                <span className="font-mono text-gray-400">+{selectedResultForOutbound.contact.phone}</span>
              </div>

              {/* Sugerencia IA */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between">
                  <label className="block text-gray-300 font-semibold">Mensaje de Seguimiento:</label>
                  <button
                    type="button"
                    disabled={generatingSuggest}
                    onClick={handleSuggestOutbound}
                    className="inline-flex items-center gap-1 text-[11px] text-purple-400 hover:text-purple-300 font-semibold cursor-pointer"
                  >
                    {generatingSuggest ? <Loader2 className="w-3 h-3 animate-spin" /> : <Bot className="w-3 h-3" />}
                    🪄 Generar Sugerencia con IA
                  </button>
                </div>

                <textarea
                  rows={4}
                  value={outboundMessage}
                  onChange={(e) => setOutboundMessage(e.target.value)}
                  placeholder="Escribe o genera con IA el mensaje de seguimiento..."
                  className="w-full bg-[#121829] border border-gray-750 focus:border-purple-500 rounded-xl p-3 text-xs text-white focus:outline-none"
                />
              </div>

              <div className="text-[10px] text-gray-400 flex items-center gap-1.5 pt-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>El envío simula presencia "escribiendo..." de 3 a 5 segundos con throttling seguro.</span>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-gray-800">
              <button
                type="button"
                onClick={() => setSelectedResultForOutbound(null)}
                className="px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold cursor-pointer"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={sendingOutbound || !outboundMessage.trim()}
                onClick={handleSendOutbound}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition cursor-pointer disabled:opacity-50"
              >
                {sendingOutbound ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Aprobar y Enviar Mensaje
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
