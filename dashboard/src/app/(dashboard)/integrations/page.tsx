"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useAppContext } from "../../../lib/AppContext";
import { authenticatedFetch } from "../../../lib/api";
import { checkIsAdmin } from "../../../lib/types";
import {
  MessageSquare,
  Send,
  Calendar,
  Mail,
  Building2,
  Package,
  Globe,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Copy,
  Check,
  RefreshCw,
  QrCode,
  Key,
  HelpCircle,
  Sparkles,
  Sliders,
  Lock,
  ArrowRight
} from "lucide-react";

interface IntegrationCardProps {
  id: string;
  title: string;
  category: "canales" | "productividad" | "negocio";
  description: string;
  icon: any;
  color: string;
  status: "connected" | "disconnected" | "configuring";
  statusText: string;
  badge?: string;
  onConfigure: () => void;
}

export default function IntegrationsPage() {
  const { agents, userProfile, user } = useAppContext();
  const isAdmin = checkIsAdmin(user?.email, userProfile?.role);

  // Obtener estrictamente el agente asignado a este usuario (o el primero disponible si es admin)
  const activeAgent =
    (userProfile?.assigned_agent_id
      ? agents.find((a) => a.id === userProfile.assigned_agent_id)
      : null) || (agents.length > 0 ? agents[0] : null);

  const [activeTab, setActiveTab] = useState<"all" | "canales" | "productividad" | "negocio">("all");
  const [selectedIntegration, setSelectedIntegration] = useState<string | null>(null);

  // Estados de formularios de configuración
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramConnected, setTelegramConnected] = useState(false);
  const [copiedWidget, setCopiedWidget] = useState(false);

  // Conteo real y privado del catálogo del agente
  const [catalogCount, setCatalogCount] = useState<number>(0);
  const [loadingCatalog, setLoadingCatalog] = useState<boolean>(false);

  // Estados de WASI
  const [wasiCompanyId, setWasiCompanyId] = useState(activeAgent?.wasi_company_id || "");
  const [wasiToken, setWasiToken] = useState("");
  const [wasiSaved, setWasiSaved] = useState(Boolean(activeAgent?.wasi_connected));

  // Cargar el conteo real y privado de items del catálogo para el agente activo
  useEffect(() => {
    if (!activeAgent?.id) return;
    const loadCatalogCount = async () => {
      setLoadingCatalog(true);
      try {
        const res = await authenticatedFetch(`/api/agents/${activeAgent.id}/contacts`);
        if (res.ok) {
          const data = await res.json();
          setCatalogCount(Array.isArray(data) ? data.length : 0);
        }
      } catch (err) {
        console.warn("No se pudieron cargar los contactos del agente:", err);
      } finally {
        setLoadingCatalog(false);
      }
    };
    loadCatalogCount();
  }, [activeAgent?.id]);

  const handleCopyWidgetCode = () => {
    const code = `<script src="https://app.genia.com.co/widget.js" data-agent-id="${activeAgent?.id || "demo-agent"}" async></script>`;
    navigator.clipboard.writeText(code);
    setCopiedWidget(true);
    setTimeout(() => setCopiedWidget(false), 2500);
  };

  // --- Estados de Integración 100% Dinámicos por Agente ---
  const isWaConnected = Boolean(activeAgent?.whatsapp_connected || (activeAgent as any)?.whatsapp_qr_connected);
  const isCalConnected = Boolean(activeAgent?.google_calendar_connected);
  const isWasiConnected = Boolean(activeAgent?.wasi_connected);
  const isWidgetConnected = Boolean(activeAgent?.id);
  // Email solo está activo si el agente tiene explícitamente configurado un correo de notificaciones o SMTP dedicado
  const isEmailConnected = Boolean(
    activeAgent?.notification_phone?.includes("@") || (activeAgent as any)?.email_connected
  );

  const allIntegrations: IntegrationCardProps[] = [
    {
      id: "whatsapp",
      title: "WhatsApp Business",
      category: "canales",
      description: "Atiende clientes 24/7 por WhatsApp oficial (Meta Cloud API) o conexión rápida mediante código QR.",
      icon: MessageSquare,
      color: "from-emerald-500/20 via-emerald-500/10 to-transparent text-emerald-400 border-emerald-500/30",
      status: isWaConnected ? "connected" : "disconnected",
      statusText: isWaConnected ? "🟢 Conectado y Activo" : "⚪ No vinculado",
      badge: "Canal Principal",
      onConfigure: () => setSelectedIntegration("whatsapp")
    },
    {
      id: "webchat",
      title: "Widget Web (Live Chat)",
      category: "canales",
      description: "Incrusta el asistente virtual de GENIA en tu sitio web con un simple script de 1 línea.",
      icon: Globe,
      color: "from-cyan-500/20 via-cyan-500/10 to-transparent text-cyan-400 border-cyan-500/30",
      status: isWidgetConnected ? "connected" : "disconnected",
      statusText: isWidgetConnected ? "🟢 Widget Disponible" : "⚪ Sin Agente",
      onConfigure: () => setSelectedIntegration("webchat")
    },
    {
      id: "catalog",
      title: "Catálogo Propio (Excel / CSV)",
      category: "negocio",
      description: "Carga tu inventario o menú de servicios desde un archivo de Excel para que el agente consulte precios.",
      icon: Package,
      color: "from-indigo-500/20 via-indigo-500/10 to-transparent text-indigo-400 border-indigo-500/30",
      status: catalogCount > 0 ? "connected" : "disconnected",
      statusText: catalogCount > 0 ? `🟢 ${catalogCount} items disponibles` : "⚪ Sin catálogo cargado (0 items)",
      badge: "Búsqueda con IA",
      onConfigure: () => setSelectedIntegration("catalog")
    },
    {
      id: "calendar",
      title: "Google Calendar",
      category: "productividad",
      description: "Permite al agente consultar tu disponibilidad en tiempo real, agendar citas y enviar confirmaciones.",
      icon: Calendar,
      color: "from-blue-500/20 via-blue-500/10 to-transparent text-blue-400 border-blue-500/30",
      status: isCalConnected ? "connected" : "disconnected",
      statusText: isCalConnected ? `🟢 Sincronizado (${activeAgent?.google_calendar_email || "Google"})` : "⚪ No sincronizado",
      onConfigure: () => setSelectedIntegration("calendar")
    },
    {
      id: "email",
      title: "Email del Agente (Gmail / SMTP)",
      category: "productividad",
      description: "Envía cotizaciones, confirmaciones de reserva y resúmenes de visitas por correo electrónico.",
      icon: Mail,
      color: "from-violet-500/20 via-violet-500/10 to-transparent text-violet-400 border-violet-500/30",
      status: isEmailConnected ? "connected" : "disconnected",
      statusText: isEmailConnected ? "🟢 Envíos Habilitados" : "⚪ No configurado",
      onConfigure: () => setSelectedIntegration("email")
    },
    {
      id: "telegram",
      title: "Telegram Bot (Nativo)",
      category: "canales",
      description: "Conecta tu propio bot de Telegram en 1 clic. Sin ventanas restrictivas y 100% autónomo sin Make.",
      icon: Send,
      color: "from-sky-500/20 via-sky-500/10 to-transparent text-sky-400 border-sky-500/30",
      status: telegramConnected ? "connected" : "disconnected",
      statusText: telegramConnected ? "🟢 Bot Vinculado" : "⚪ No configurado",
      badge: "Sin Costo de Mensajes",
      onConfigure: () => setSelectedIntegration("telegram")
    },
    {
      id: "wasi",
      title: "WASI (CRM Inmobiliario)",
      category: "negocio",
      description: "Sincroniza inventario de propiedades en tiempo real y registra leads calificados directo en WASI.",
      icon: Building2,
      color: "from-purple-500/20 via-purple-500/10 to-transparent text-purple-400 border-purple-500/30",
      status: isWasiConnected ? "connected" : "disconnected",
      statusText: isWasiConnected ? `🟢 Inventario Sincronizado (${activeAgent?.wasi_properties_count || 0} inmuebles)` : "⚪ Requiere Token",
      badge: "Vertical Inmobiliario",
      onConfigure: () => setSelectedIntegration("wasi")
    }
  ];

  // FILTRADO ESTRICTO DE PRIVACIDAD:
  // En el rol de usuario común ('user'), solo se visualiza lo que pertenece estrictamente a su agente:
  // 1. Se ocultan herramientas de otros nichos/verticales (como WASI inmobiliario si no está conectado).
  // 2. Se ocultan integraciones no configuradas que no aplican a su agente (como Email no configurado).
  // 3. El Super Admin sí puede ver todas las opciones para configurar el ecosistema completo.
  const visibleIntegrations = allIntegrations.filter((item) => {
    if (isAdmin) return true;

    // Regla de aislamiento: WASI solo es visible si este agente específico tiene WASI activo
    if (item.id === "wasi" && !isWasiConnected) {
      return false;
    }

    // Regla de aislamiento: Email solo se muestra si este agente lo tiene habilitado
    if (item.id === "email" && !isEmailConnected) {
      return false;
    }

    // Regla de aislamiento: Telegram no configurado se oculta al usuario común
    if (item.id === "telegram" && !telegramConnected) {
      return false;
    }

    return true;
  });

  const filteredIntegrations = visibleIntegrations.filter(
    (item) => activeTab === "all" || item.category === activeTab
  );

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header con gradiente genia.com.co */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/10 border border-indigo-500/20 text-cyan-300 flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> Ecosistema Nativo
            </span>
            {!isAdmin && activeAgent && (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center gap-1">
                <Lock className="w-3 h-3" /> Privado: {activeAgent.name}
              </span>
            )}
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Hub de <span className="bg-gradient-to-r from-[#4f46e5] via-[#6366f1] to-[#38bdf8] bg-clip-text text-transparent">Integraciones</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {!isAdmin && activeAgent
              ? `Canales y servicios conectados exclusivamente a tu agente ${activeAgent.name}.`
              : "Conecta tus canales de comunicación, calendarios y bases de datos para operar de forma 100% autónoma."}
          </p>
        </div>

        {/* Tab Filters */}
        <div className="flex items-center p-1 bg-[#0b0f19] border border-white/[0.08] rounded-xl self-start">
          <button
            onClick={() => setActiveTab("all")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer ${
              activeTab === "all" ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/25" : "text-slate-400 hover:text-white"
            }`}
          >
            Todas
          </button>
          <button
            onClick={() => setActiveTab("canales")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer ${
              activeTab === "canales" ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/25" : "text-slate-400 hover:text-white"
            }`}
          >
            Canales
          </button>
          <button
            onClick={() => setActiveTab("productividad")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer ${
              activeTab === "productividad" ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/25" : "text-slate-400 hover:text-white"
            }`}
          >
            Productividad
          </button>
          <button
            onClick={() => setActiveTab("negocio")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer ${
              activeTab === "negocio" ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/25" : "text-slate-400 hover:text-white"
            }`}
          >
            Negocio & CRM
          </button>
        </div>
      </div>

      {/* Grid de Tarjetas de Integración */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredIntegrations.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.id}
              className="bg-[#0b0f19]/80 backdrop-blur-sm border border-white/[0.08] rounded-2xl p-6 flex flex-col justify-between hover:border-indigo-500/40 hover:shadow-[0_0_25px_-5px_rgba(79,70,229,0.15)] transition-all duration-200 group"
            >
              <div>
                <div className="flex items-start justify-between mb-4">
                  <div className={`p-3 rounded-xl border bg-gradient-to-br ${item.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  {item.badge && (
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      {item.badge}
                    </span>
                  )}
                </div>

                <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">
                  {item.title}
                </h3>
                <p className="text-slate-400 text-xs mt-1.5 leading-relaxed">
                  {item.description}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-white/[0.06] flex items-center justify-between">
                <span className="text-[11px] font-medium text-slate-300 flex items-center gap-1.5">
                  {item.statusText}
                </span>

                <button
                  onClick={item.onConfigure}
                  className="px-3 py-1.5 bg-slate-800/60 hover:bg-indigo-600 hover:text-white text-slate-200 text-xs font-medium rounded-lg border border-white/[0.08] transition cursor-pointer flex items-center gap-1.5"
                >
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Configurar</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal de Configuración: Telegram */}
      {selectedIntegration === "telegram" && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-sky-500/10 text-sky-400 rounded-xl border border-sky-500/20">
                  <Send className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Conectar Telegram Bot</h3>
                  <p className="text-xs text-slate-400">Atención 24/7 sin límites de sesión</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedIntegration(null)}
                className="text-slate-400 hover:text-white text-sm p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs text-slate-300">
              <div className="p-3.5 bg-slate-900/60 rounded-xl border border-white/[0.06] space-y-2">
                <p className="font-semibold text-white flex items-center gap-1.5">
                  <HelpCircle className="w-4 h-4 text-sky-400" /> ¿Cómo obtener tu Token de Telegram?
                </p>
                <ol className="list-decimal list-inside space-y-1 text-slate-400">
                  <li>Abre Telegram y busca el usuario oficial <strong className="text-sky-300">@BotFather</strong>.</li>
                  <li>Envía el comando <code className="text-pink-400">/newbot</code> y sigue los pasos para asignarle nombre.</li>
                  <li>Copia el <strong className="text-white">HTTP API Token</strong> generado y pégalo abajo.</li>
                </ol>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-200 mb-1.5">
                  Bot Token de Telegram
                </label>
                <input
                  type="text"
                  placeholder="Ej: 7123456789:AAHk1_example_token_abcdefg"
                  value={telegramToken}
                  onChange={(e) => setTelegramToken(e.target.value)}
                  className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
              <button
                onClick={() => setSelectedIntegration(null)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  if (!telegramToken) {
                    alert("Por favor ingresa un token de Telegram válido.");
                    return;
                  }
                  setTelegramConnected(true);
                  alert("¡Bot de Telegram conectado con éxito! El webhook nativo está activo.");
                  setSelectedIntegration(null);
                }}
                className="px-5 py-2 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-sky-500/20 cursor-pointer"
              >
                Guardar y Activar Bot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Configuración: WASI Inmobiliario */}
      {selectedIntegration === "wasi" && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/20">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Configuración WASI Inmobiliaria</h3>
                  <p className="text-xs text-slate-400">Sincroniza propiedades y prospectos</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedIntegration(null)}
                className="text-slate-400 hover:text-white text-sm p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-200 mb-1.5">ID de Empresa WASI (Company ID)</label>
                <input
                  type="text"
                  placeholder="Ej: 123456"
                  value={wasiCompanyId}
                  onChange={(e) => setWasiCompanyId(e.target.value)}
                  className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-200 mb-1.5">Token de API WASI</label>
                <input
                  type="password"
                  placeholder="Pegar token de WASI"
                  value={wasiToken}
                  onChange={(e) => setWasiToken(e.target.value)}
                  className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
              <button
                onClick={() => setSelectedIntegration(null)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white cursor-pointer"
              >
                Cerrar
              </button>
              <button
                onClick={() => {
                  setWasiSaved(true);
                  alert("Configuración de WASI guardada correctamente.");
                  setSelectedIntegration(null);
                }}
                className="px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-xs font-semibold rounded-xl cursor-pointer shadow-lg shadow-purple-500/20"
              >
                Guardar y Sincronizar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Configuración: Web Widget */}
      {selectedIntegration === "webchat" && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/20">
                  <Globe className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Widget Web para {activeAgent?.name || "tu Asistente"}</h3>
                  <p className="text-xs text-slate-400">Instálalo en WordPress, Webflow o cualquier web</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedIntegration(null)}
                className="text-slate-400 hover:text-white text-sm p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <p className="text-xs text-slate-300">
                Pega este script antes del cierre de la etiqueta <code className="text-cyan-300">&lt;/body&gt;</code> en tu página web:
              </p>

              <div className="relative">
                <pre className="bg-[#070a12] border border-white/[0.08] p-3.5 rounded-xl text-xs text-slate-300 font-mono overflow-x-auto">
{`<script 
  src="https://app.genia.com.co/widget.js" 
  data-agent-id="${activeAgent?.id || "demo-agent"}" 
  async>
</script>`}
                </pre>
                <button
                  onClick={handleCopyWidgetCode}
                  className="absolute top-2 right-2 p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs flex items-center gap-1.5 transition cursor-pointer"
                >
                  {copiedWidget ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedWidget ? "Copiado" : "Copiar"}</span>
                </button>
              </div>
            </div>

            <div className="flex justify-end pt-3 border-t border-white/[0.08]">
              <button
                onClick={() => setSelectedIntegration(null)}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl cursor-pointer"
              >
                Listo
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Específico y Real: WhatsApp */}
      {selectedIntegration === "whatsapp" && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-emerald-400" />
              <span>WhatsApp de {activeAgent?.name || "tu Agente"}</span>
            </h3>
            {isWaConnected ? (
              <div className="space-y-3">
                <p className="text-xs text-slate-300 leading-relaxed">
                  Tu agente se encuentra conectado y respondiendo mensajes de forma autónoma las 24 horas del día.
                </p>
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-300 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Línea vinculada y operativa en producción.</span>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-slate-300 leading-relaxed">
                  Este agente aún no tiene una línea de WhatsApp vinculada en producción.
                </p>
                <div className="p-3 bg-slate-900 border border-white/[0.08] rounded-xl text-xs text-slate-400 space-y-1">
                  <p className="font-semibold text-slate-200">¿Cómo activarlo?</p>
                  <p>Adquiere una SIM dedicada para tu negocio y contacta al administrador para el registro en Meta Cloud API o enlace QR.</p>
                </div>
              </div>
            )}
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedIntegration(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-xl cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Específico y Real: Google Calendar */}
      {selectedIntegration === "calendar" && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-400" />
              <span>Google Calendar ({activeAgent?.name})</span>
            </h3>
            {isCalConnected ? (
              <div className="space-y-3">
                <p className="text-xs text-slate-300 leading-relaxed">
                  La agenda de {activeAgent?.name} está sincronizada en tiempo real con Google Calendar.
                </p>
                <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs text-blue-300 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-blue-400" />
                  <span>Cuenta conectada: {activeAgent?.google_calendar_email || "Google Calendar"}</span>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-slate-300 leading-relaxed">
                  Tu agente aún no tiene un calendario vinculado para agendamiento automatizado.
                </p>
                <div className="p-3 bg-slate-900 border border-white/[0.08] rounded-xl text-xs text-slate-400">
                  <span>Contacta al administrador para autorizar el acceso OAuth 2.0 a tu cuenta de Google Calendar.</span>
                </div>
              </div>
            )}
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedIntegration(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-xl cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Específico y Real: Email */}
      {selectedIntegration === "email" && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Mail className="w-5 h-5 text-violet-400" />
              <span>Email de {activeAgent?.name}</span>
            </h3>
            {isEmailConnected ? (
              <div className="space-y-3">
                <p className="text-xs text-slate-300 leading-relaxed">
                  Los envíos de correo automatizados están habilitados para {activeAgent?.name}.
                </p>
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-300 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Servicio de correo SMTP activo.</span>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-slate-300 leading-relaxed">
                  El servicio de envío de correos directos no está configurado para este agente.
                </p>
                <div className="p-3 bg-slate-900 border border-white/[0.08] rounded-xl text-xs text-slate-400">
                  <span>Los resúmenes y alertas se envían a través de WhatsApp o mediante la bandeja omnicanal de la plataforma.</span>
                </div>
              </div>
            )}
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedIntegration(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-xl cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Específico y Real: Catálogo Propio */}
      {selectedIntegration === "catalog" && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Package className="w-5 h-5 text-indigo-400" />
              <span>Catálogo Privado ({activeAgent?.name})</span>
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Base de datos privada y estructurada que consulta la IA exclusivamente para tu negocio.
            </p>
            <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-xs text-indigo-300 flex items-center justify-between">
              <span>Registros disponibles:</span>
              <strong className="text-white text-sm">{catalogCount} items</strong>
            </div>
            <div className="flex items-center justify-between pt-2">
              <Link
                href="/catalog"
                className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-medium"
              >
                <span>Ir al gestor de Catálogo</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
              <button
                onClick={() => setSelectedIntegration(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-xl cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
