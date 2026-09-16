"use client";

import { useState } from "react";
import { useAppContext } from "../../../lib/AppContext";
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
  Sliders
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
  const { agents } = useAppContext();
  const activeAgent = agents.length > 0 ? agents[0] : null;

  const [activeTab, setActiveTab] = useState<"all" | "canales" | "productividad" | "negocio">("all");
  const [selectedIntegration, setSelectedIntegration] = useState<string | null>(null);

  // Estados de formularios de configuración
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramConnected, setTelegramConnected] = useState(false);
  const [copiedWidget, setCopiedWidget] = useState(false);

  // Estados de WASI
  const [wasiCompanyId, setWasiCompanyId] = useState(activeAgent?.wasi_company_id || "");
  const [wasiToken, setWasiToken] = useState("");
  const [wasiSaved, setWasiSaved] = useState(Boolean(activeAgent?.wasi_connected));

  const handleCopyWidgetCode = () => {
    const code = `<script src="https://app.genia.com.co/widget.js" data-agent-id="${activeAgent?.id || "demo-agent"}" async></script>`;
    navigator.clipboard.writeText(code);
    setCopiedWidget(true);
    setTimeout(() => setCopiedWidget(false), 2500);
  };

  const integrationsList: IntegrationCardProps[] = [
    {
      id: "whatsapp",
      title: "WhatsApp Business",
      category: "canales",
      description: "Atiende clientes 24/7 por WhatsApp oficial (Meta Cloud API) o conexión rápida mediante código QR.",
      icon: MessageSquare,
      color: "from-emerald-500/20 via-emerald-500/10 to-transparent text-emerald-400 border-emerald-500/30",
      status: "connected",
      statusText: "🟢 Conectado y Activo",
      badge: "Canal Principal",
      onConfigure: () => setSelectedIntegration("whatsapp")
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
      id: "calendar",
      title: "Google Calendar",
      category: "productividad",
      description: "Permite al agente consultar tu disponibilidad en tiempo real, agendar citas y enviar confirmaciones.",
      icon: Calendar,
      color: "from-blue-500/20 via-blue-500/10 to-transparent text-blue-400 border-blue-500/30",
      status: "connected",
      statusText: "🟢 Agenda Sincronizada",
      onConfigure: () => setSelectedIntegration("calendar")
    },
    {
      id: "email",
      title: "Email del Agente (Gmail / SMTP)",
      category: "productividad",
      description: "Envía cotizaciones, confirmaciones de reserva y resúmenes de visitas por correo electrónico.",
      icon: Mail,
      color: "from-violet-500/20 via-violet-500/10 to-transparent text-violet-400 border-violet-500/30",
      status: "connected",
      statusText: "🟢 Envíos Habilitados (Spacemail)",
      onConfigure: () => setSelectedIntegration("email")
    },
    {
      id: "wasi",
      title: "WASI (CRM Inmobiliario)",
      category: "negocio",
      description: "Sincroniza inventario de propiedades en tiempo real y registra leads calificados directo en WASI.",
      icon: Building2,
      color: "from-purple-500/20 via-purple-500/10 to-transparent text-purple-400 border-purple-500/30",
      status: wasiSaved ? "connected" : "disconnected",
      statusText: wasiSaved ? "🟢 Inventario Sincronizado" : "⚪ Requiere Token",
      badge: "Vertical Inmobiliario",
      onConfigure: () => setSelectedIntegration("wasi")
    },
    {
      id: "catalog",
      title: "Catálogo Propio (Excel / CSV)",
      category: "negocio",
      description: "Carga tu inventario o menú de servicios desde un archivo de Excel para que el agente consulte precios.",
      icon: Package,
      color: "from-indigo-500/20 via-indigo-500/10 to-transparent text-indigo-400 border-indigo-500/30",
      status: "connected",
      statusText: "🟢 120 items disponibles",
      badge: "Búsqueda con IA",
      onConfigure: () => setSelectedIntegration("catalog")
    },
    {
      id: "webchat",
      title: "Widget Web (Live Chat)",
      category: "canales",
      description: "Incrusta el asistente virtual de GENIA en tu sitio web con un simple script de 1 línea.",
      icon: Globe,
      color: "from-cyan-500/20 via-cyan-500/10 to-transparent text-cyan-400 border-cyan-500/30",
      status: "connected",
      statusText: "🟢 Widget Disponible",
      onConfigure: () => setSelectedIntegration("webchat")
    }
  ];

  const filteredIntegrations = integrationsList.filter(
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
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Hub de <span className="bg-gradient-to-r from-[#4f46e5] via-[#6366f1] to-[#38bdf8] bg-clip-text text-transparent">Integraciones</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Conecta tus canales de comunicación, calendarios y bases de datos para operar de forma 100% autónoma.
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
                  <h3 className="text-lg font-bold text-white">Widget para tu Sitio Web</h3>
                  <p className="text-xs text-slate-400">Instálalo en WordPress, Webflow o HTML</p>
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
                Pega este código antes del cierre de la etiqueta <code className="text-cyan-300">&lt;/body&gt;</code> en tu página web:
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

      {/* Modal Genérico para WhatsApp / Calendar / Email / Catalog */}
      {["whatsapp", "calendar", "email", "catalog"].includes(selectedIntegration || "") && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white capitalize">
              Estado de {selectedIntegration}
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Este módulo se encuentra vinculado y operativo de forma nativa por el motor de GENIA. 
              Los eventos y respuestas se procesan automáticamente 24/7 sin intermediarios.
            </p>
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Conexión saludable y activa.</span>
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedIntegration(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-xl cursor-pointer"
              >
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
