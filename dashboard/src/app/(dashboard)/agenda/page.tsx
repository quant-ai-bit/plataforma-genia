"use client";

import { useState } from "react";
import {
  Calendar as CalendarIcon,
  Clock,
  User,
  Phone,
  MessageSquare,
  CheckCircle2,
  XCircle,
  Sparkles,
  ExternalLink,
  RefreshCw,
  Plus
} from "lucide-react";

interface Appointment {
  id: string;
  clientName: string;
  phone: string;
  serviceOrProperty: string;
  date: string;
  time: string;
  status: "confirmed" | "pending" | "completed" | "cancelled";
  channel: "whatsapp" | "telegram" | "web";
}

export default function AgendaPage() {
  const [filter, setFilter] = useState<string>("all");

  const [appointments, setAppointments] = useState<Appointment[]>([
    {
      id: "apt-1",
      clientName: "Carolina Escarria",
      phone: "573105551234",
      serviceOrProperty: "Visita Apartamento 402 Laureles",
      date: "Hoy, 16 Sep",
      time: "3:00 PM",
      status: "confirmed",
      channel: "whatsapp"
    },
    {
      id: "apt-2",
      clientName: "Felipe Restrepo",
      phone: "573004445678",
      serviceOrProperty: "Valoración Limpieza Facial",
      date: "Mañana, 17 Sep",
      time: "10:30 AM",
      status: "confirmed",
      channel: "whatsapp"
    },
    {
      id: "apt-3",
      clientName: "Mariana Gómez",
      phone: "573158889012",
      serviceOrProperty: "Reserva Mesa 4 Personas",
      date: "Viernes, 19 Sep",
      time: "8:00 PM",
      status: "pending",
      channel: "telegram"
    }
  ]);

  const toggleStatus = (id: string, newStatus: Appointment["status"]) => {
    setAppointments((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: newStatus } : a))
    );
  };

  const filteredAppointments = appointments.filter(
    (a) => filter === "all" || a.status === filter
  );

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header con gradiente genia.com.co */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/10 border border-indigo-500/20 text-cyan-300 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-cyan-400" /> Sincronización Automática
            </span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Agenda & <span className="bg-gradient-to-r from-[#4f46e5] via-[#6366f1] to-[#38bdf8] bg-clip-text text-transparent">Citas</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Visitas y reuniones agendadas por tu agente de IA directamente en tu Google Calendar.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => alert("Agenda sincronizada con Google Calendar.")}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-white/[0.08] transition cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
            <span>Sincronizar Google Calendar</span>
          </button>
        </div>
      </div>

      {/* Resumen de Métricas */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[#0b0f19] border border-white/[0.08] p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Citas Esta Semana</span>
          <p className="text-2xl font-black text-white">8 Citas</p>
          <span className="text-[11px] text-emerald-400">100% coordinadas por IA</span>
        </div>
        <div className="bg-[#0b0f19] border border-white/[0.08] p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Próxima Visita</span>
          <p className="text-2xl font-black text-cyan-300">Hoy 3:00 PM</p>
          <span className="text-[11px] text-slate-400">Carolina Escarria (Laureles)</span>
        </div>
        <div className="bg-[#0b0f19] border border-white/[0.08] p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Estado de Conexión</span>
          <p className="text-2xl font-black text-emerald-400 flex items-center gap-2">
            <CheckCircle2 className="w-6 h-6" /> Activo
          </p>
          <span className="text-[11px] text-slate-400">Google Calendar Conectado</span>
        </div>
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-2 p-1.5 bg-[#0b0f19] border border-white/[0.08] rounded-2xl w-fit">
        {[
          { id: "all", label: "Todas las Citas" },
          { id: "confirmed", label: "🟢 Confirmadas" },
          { id: "pending", label: "🟡 Pendientes" },
          { id: "completed", label: "🔵 Completadas" }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilter(tab.id)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-medium transition cursor-pointer ${
              filter === tab.id
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/20"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Lista de Citas */}
      <div className="space-y-3">
        {filteredAppointments.map((apt) => (
          <div
            key={apt.id}
            className="bg-[#0b0f19] border border-white/[0.08] hover:border-indigo-500/30 p-5 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all"
          >
            <div className="flex items-start gap-4">
              <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                <CalendarIcon className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-white text-sm">{apt.clientName}</h3>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-white/[0.08] uppercase">
                    {apt.channel}
                  </span>
                </div>
                <p className="text-xs text-cyan-300 font-medium">{apt.serviceOrProperty}</p>
                <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                  <span className="flex items-center gap-1 font-mono text-white">
                    <Clock className="w-3.5 h-3.5 text-indigo-400" /> {apt.date} a las {apt.time}
                  </span>
                  <a
                    href={`https://wa.me/${apt.phone}`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-emerald-400 hover:underline"
                  >
                    <Phone className="w-3.5 h-3.5" /> +{apt.phone}
                  </a>
                </div>
              </div>
            </div>

            {/* Acciones */}
            <div className="flex items-center gap-2 self-end md:self-auto">
              {apt.status === "pending" && (
                <button
                  onClick={() => toggleStatus(apt.id, "confirmed")}
                  className="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl text-xs font-semibold cursor-pointer"
                >
                  Confirmar
                </button>
              )}
              {apt.status === "confirmed" && (
                <button
                  onClick={() => toggleStatus(apt.id, "completed")}
                  className="px-3 py-1.5 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-xl text-xs font-semibold cursor-pointer"
                >
                  Marcar Realizada
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
