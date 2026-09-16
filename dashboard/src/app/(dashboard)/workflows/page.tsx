"use client";

import { useState } from "react";
import {
  GitBranch,
  Sparkles,
  Play,
  Clock,
  MessageSquare,
  CheckCircle2,
  Calendar,
  AlertTriangle,
  Building2,
  Utensils,
  Plus,
  Sliders,
  Power,
  ChevronRight,
  ShieldCheck,
  Zap,
  ArrowRight
} from "lucide-react";

interface WorkflowItem {
  id: string;
  title: string;
  industry: "bienes_raices" | "restaurantes" | "clinicas" | "rentas_cortas" | "general";
  industryLabel: string;
  trigger: string;
  actionsCount: number;
  steps: {
    type: "trigger" | "delay" | "action" | "condition";
    title: string;
    detail: string;
  }[];
  active: boolean;
  executionsCount: number;
}

export default function WorkflowsPage() {
  const [activeFilter, setActiveFilter] = useState<string>("all");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowItem | null>(null);

  const [workflows, setWorkflows] = useState<WorkflowItem[]>([
    {
      id: "wf-1",
      title: "Seguimiento Automático de Visita a Inmueble",
      industry: "bienes_raices",
      industryLabel: "Bienes Raíces",
      trigger: "📅 Visita agendada en calendario",
      actionsCount: 3,
      active: true,
      executionsCount: 48,
      steps: [
        { type: "trigger", title: "Disparador", detail: "Lead agenda visita a una propiedad" },
        { type: "action", title: "Paso 1 (Inmediato)", detail: "Enviar confirmación WhatsApp con ubicación Google Maps y ficha" },
        { type: "delay", title: "Espera / Temporizador", detail: "Pausar hasta 2 horas antes de la cita" },
        { type: "action", title: "Paso 2 (Recordatorio)", detail: "¿Nos confirmas tu llegada al apartamento a las 3:00 PM?" },
        { type: "delay", title: "Espera / Post-visita", detail: "Pausar 1 hora después de la cita" },
        { type: "action", title: "Paso 3 (Feedback)", detail: "¿Qué te pareció el inmueble? ¿Deseas presentar una oferta?" }
      ]
    },
    {
      id: "wf-2",
      title: "Confirmación y Reseña de Mesa en Restaurante",
      industry: "restaurantes",
      industryLabel: "Restaurantes",
      trigger: "🍽️ Reserva de mesa solicitada",
      actionsCount: 3,
      active: true,
      executionsCount: 132,
      steps: [
        { type: "trigger", title: "Disparador", detail: "Cliente solicita reserva para almuerzo o cena" },
        { type: "action", title: "Paso 1 (Inmediato)", detail: "Confirmar aforo, registrar número de personas y enviar confirmación" },
        { type: "delay", title: "Espera", detail: "3 horas antes de la hora reservada" },
        { type: "action", title: "Paso 2 (Reconfirmación)", detail: "Recordatorio con botones 'Confirmar' o 'Cancelar'" },
        { type: "delay", title: "Espera Post-Cena", detail: "Al día siguiente a las 11:00 AM" },
        { type: "action", title: "Paso 3 (Reseña)", detail: "¿Cómo estuvo tu comida? Si responde 5⭐ -> Enlace a Google Reviews" }
      ]
    },
    {
      id: "wf-3",
      title: "Check-in y Check-out Autónomo para Rentas Cortas",
      industry: "rentas_cortas",
      industryLabel: "Rentas Cortas / Airbnb",
      trigger: "🏖️ Reserva confirmada en plataforma",
      actionsCount: 4,
      active: false,
      executionsCount: 29,
      steps: [
        { type: "trigger", title: "Disparador", detail: "Huésped confirma reserva de propiedad" },
        { type: "delay", title: "Espera previa", detail: "24 horas antes de la llegada" },
        { type: "action", title: "Paso 1 (Llegada)", detail: "Enviar código de chapa electrónica e instrucciones de parqueadero" },
        { type: "delay", title: "Día de salida", detail: "El día del check-out a las 9:30 AM" },
        { type: "action", title: "Paso 2 (Salida)", detail: "Recordatorio de check-out a las 11:00 AM y depósito de llaves" }
      ]
    },
    {
      id: "wf-4",
      title: "Cuidados y Control Post-Procedimiento Estético",
      industry: "clinicas",
      industryLabel: "Clínicas Estéticas",
      trigger: "💉 Procedimiento marcado como realizado",
      actionsCount: 3,
      active: true,
      executionsCount: 76,
      steps: [
        { type: "trigger", title: "Disparador", detail: "Paciente completa su tratamiento" },
        { type: "action", title: "Paso 1 (Inmediato)", detail: "Enviar recomendaciones médicas: aplicación de hielo y reposo" },
        { type: "delay", title: "Espera 48 horas", detail: "2 días después del procedimiento" },
        { type: "action", title: "Paso 2 (Evolución)", detail: "¿Cómo va la recuperación de tu piel? Escríbenos ante cualquier duda" },
        { type: "delay", title: "Espera 7 días", detail: "1 semana después" },
        { type: "action", title: "Paso 3 (Cita de control)", detail: "Agendamiento automático de cita de revisión con el especialista" }
      ]
    },
    {
      id: "wf-5",
      title: "Reactivación Automática de Prospectos Inactivos",
      industry: "general",
      industryLabel: "General / Ventas",
      trigger: "⏰ 48 horas sin respuesta del cliente",
      actionsCount: 2,
      active: true,
      executionsCount: 210,
      steps: [
        { type: "trigger", title: "Disparador", detail: "Lead no responde tras recibir la cotización" },
        { type: "action", title: "Paso 1 (Reenganche)", detail: "Hola {nombre}, ¿pudiste revisar la información? Cuéntame si tienes dudas" },
        { type: "condition", title: "Condición", detail: "Si no responde en 24h adicionales" },
        { type: "action", title: "Paso 2 (Alerta)", detail: "Notificar al asesor comercial por WhatsApp para llamada telefónica" }
      ]
    }
  ]);

  const toggleWorkflow = (id: string) => {
    setWorkflows((prev) =>
      prev.map((wf) => (wf.id === id ? { ...wf, active: !wf.active } : wf))
    );
  };

  const filteredWorkflows = workflows.filter(
    (wf) => activeFilter === "all" || wf.industry === activeFilter
  );

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header con gradiente genia.com.co */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/10 border border-indigo-500/20 text-cyan-300 flex items-center gap-1">
              <Zap className="w-3 h-3 text-cyan-400" /> Motor Nativo Autónomo
            </span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Flujos & <span className="bg-gradient-to-r from-[#4f46e5] via-[#6366f1] to-[#38bdf8] bg-clip-text text-transparent">Automatizaciones</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Ejecuta secuencias de mensajes, recordatorios y acciones operativas 100% nativas sin suscripciones a Make o Zapier.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 text-white rounded-xl text-xs font-bold border border-indigo-500/30 shadow-lg shadow-indigo-500/25 transition cursor-pointer self-start"
        >
          <Plus className="w-4 h-4" />
          <span>Crear Nuevo Flujo</span>
        </button>
      </div>

      {/* Filter Tabs por Industria */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 bg-[#0b0f19] border border-white/[0.08] rounded-2xl w-fit">
        {[
          { id: "all", label: "Todos los Flujos" },
          { id: "bienes_raices", label: "🏠 Bienes Raíces" },
          { id: "restaurantes", label: "🍽️ Restaurantes" },
          { id: "clinicas", label: "💉 Clínicas" },
          { id: "rentas_cortas", label: "🏖️ Rentas Cortas" },
          { id: "general", label: "⚙️ Ventas Generales" }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveFilter(tab.id)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-medium transition cursor-pointer ${
              activeFilter === tab.id
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/20"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Lista de Flujos de Automatización */}
      <div className="grid grid-cols-1 gap-4">
        {filteredWorkflows.map((wf) => (
          <div
            key={wf.id}
            className="bg-[#0b0f19]/80 backdrop-blur-sm border border-white/[0.08] hover:border-indigo-500/30 rounded-2xl p-5 transition-all duration-200"
          >
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2.5">
                  <span className="px-2.5 py-0.5 rounded-md text-[10px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                    {wf.industryLabel}
                  </span>
                  <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                    <Clock className="w-3 h-3 text-slate-500" /> {wf.executionsCount} ejecuciones
                  </span>
                </div>

                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-cyan-400" />
                  {wf.title}
                </h3>
                <p className="text-xs text-slate-400 flex items-center gap-1.5">
                  <span className="font-semibold text-slate-300">Disparador:</span> {wf.trigger}
                </p>
              </div>

              {/* Controles del Flujo */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSelectedWorkflow(wf)}
                  className="px-3 py-1.5 bg-slate-800/60 hover:bg-slate-700/80 text-slate-300 text-xs font-medium rounded-xl border border-white/[0.08] transition cursor-pointer flex items-center gap-1.5"
                >
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Ver Pasos</span>
                </button>

                <button
                  onClick={() => toggleWorkflow(wf.id)}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold border transition cursor-pointer ${
                    wf.active
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                      : "bg-slate-800/40 text-slate-500 border-slate-700/50 hover:text-slate-300"
                  }`}
                >
                  <Power className="w-3.5 h-3.5" />
                  <span>{wf.active ? "Activo" : "Pausado"}</span>
                </button>
              </div>
            </div>

            {/* Visualizador de la línea de tiempo del flujo */}
            <div className="mt-4 pt-4 border-t border-white/[0.06] flex items-center gap-2 overflow-x-auto pb-1 text-xs">
              {wf.steps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-2 flex-shrink-0">
                  <div
                    className={`px-3 py-1.5 rounded-lg text-[11px] font-medium border flex items-center gap-1.5 ${
                      step.type === "trigger"
                        ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/20"
                        : step.type === "delay"
                        ? "bg-amber-500/10 text-amber-300 border-amber-500/20"
                        : step.type === "condition"
                        ? "bg-purple-500/10 text-purple-300 border-purple-500/20"
                        : "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                    }`}
                  >
                    <span>{step.title}</span>
                  </div>
                  {idx < wf.steps.length - 1 && (
                    <ArrowRight className="w-3 h-3 text-slate-600 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Modal de Detalle de Pasos */}
      {selectedWorkflow && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  {selectedWorkflow.industryLabel}
                </span>
                <h3 className="text-lg font-bold text-white mt-1">{selectedWorkflow.title}</h3>
              </div>
              <button
                onClick={() => setSelectedWorkflow(null)}
                className="text-slate-400 hover:text-white p-1 text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
              {selectedWorkflow.steps.map((step, idx) => (
                <div
                  key={idx}
                  className="p-3.5 bg-[#070a12] border border-white/[0.08] rounded-xl flex items-start gap-3"
                >
                  <div className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-300 font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                    {idx + 1}
                  </div>
                  <div className="space-y-0.5 flex-1">
                    <p className="text-xs font-bold text-white">{step.title}</p>
                    <p className="text-xs text-slate-400 leading-relaxed">{step.detail}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-3 border-t border-white/[0.08]">
              <button
                onClick={() => setSelectedWorkflow(null)}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Crear Nuevo Flujo */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-400" /> Crear Flujo de Automatización
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white p-1 text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-200 mb-1.5">Nombre del Flujo</label>
                <input
                  type="text"
                  placeholder="Ej: Recordatorio de cita 2 horas antes"
                  className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-200 mb-1.5">Disparador (Trigger)</label>
                <select className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer">
                  <option>📩 Mensaje recibido por WhatsApp o Telegram</option>
                  <option>📅 Cita agendada en Google Calendar</option>
                  <option>👤 Lead cambia de etapa en el CRM</option>
                  <option>⏰ Inactividad de 48 horas</option>
                  <option>🏠 Nuevo inmueble cargado en WASI</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-200 mb-1.5">Acción Principal</label>
                <select className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer">
                  <option>💬 Enviar mensaje por WhatsApp con IA</option>
                  <option>✈️ Enviar mensaje por Telegram</option>
                  <option>📧 Enviar correo electrónico con cotización</option>
                  <option>🔔 Notificar al asesor comercial</option>
                  <option>📊 Mover lead en el Pipeline CRM</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  alert("Flujo creado con éxito. El motor nativo de GENIA lo ejecutará en tiempo real.");
                  setShowCreateModal(false);
                }}
                className="px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-xs font-semibold rounded-xl cursor-pointer shadow-lg shadow-indigo-500/25"
              >
                Crear y Activar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
