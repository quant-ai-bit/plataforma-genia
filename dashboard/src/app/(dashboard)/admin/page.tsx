"use client";

import { useState } from "react";
import Link from "next/link";
import { useAppContext } from "../../../lib/AppContext";
import {
  ShieldAlert,
  Users,
  Bot,
  Layers,
  Sparkles,
  ExternalLink,
  Settings,
  Sliders,
  CheckCircle2,
  Lock,
  ArrowUpRight,
  UserCheck,
  ShieldCheck,
  Activity
} from "lucide-react";

interface ClientSubaccount {
  id: string;
  name: string;
  industry: string;
  assignedAgentName: string;
  agentId: string;
  tier: "esencial" | "pro" | "business" | "enterprise";
  tierPrice: string;
  channels: string[];
  status: "active" | "pending";
}

export default function AdminMasterPage() {
  const { agents, userProfile } = useAppContext();

  // Lista de subcuentas simuladas o vinculadas
  const [subaccounts, setSubaccounts] = useState<ClientSubaccount[]>([
    {
      id: "sub-1",
      name: "Inmobiliaria El Triunfo",
      industry: "Bienes Raíces",
      assignedAgentName: "Agente Comercial Inmobiliario (WASI)",
      agentId: agents.length > 0 ? agents[0].id : "agent-1",
      tier: "business",
      tierPrice: "$997.000 COP/mes",
      channels: ["WhatsApp", "WASI", "Calendar"],
      status: "active"
    },
    {
      id: "sub-2",
      name: "Clínica Serena Estética",
      industry: "Salud & Estética",
      assignedAgentName: "Asistente Agendamiento y Servicios",
      agentId: agents.length > 1 ? agents[1].id : "agent-2",
      tier: "pro",
      tierPrice: "$497.000 COP/mes",
      channels: ["WhatsApp", "Telegram", "Calendar"],
      status: "active"
    },
    {
      id: "sub-3",
      name: "Plantas Eléctricas Carolina Escarria",
      industry: "Operaciones & Soporte",
      assignedAgentName: "Agente Operativo Técnico",
      agentId: agents.length > 0 ? agents[0].id : "agent-3",
      tier: "enterprise",
      tierPrice: "$1.997.000 COP/mes",
      channels: ["WhatsApp", "Base Datos Excel", "Workflows"],
      status: "active"
    }
  ]);

  const [selectedSubaccount, setSelectedSubaccount] = useState<ClientSubaccount | null>(null);

  const handleUpdateTier = (id: string, newTier: ClientSubaccount["tier"]) => {
    const prices: Record<ClientSubaccount["tier"], string> = {
      esencial: "$197.000 COP/mes",
      pro: "$497.000 COP/mes",
      business: "$997.000 COP/mes",
      enterprise: "$1.997.000 COP/mes"
    };

    setSubaccounts((prev) =>
      prev.map((s) =>
        s.id === id ? { ...s, tier: newTier, tierPrice: prices[newTier] } : s
      )
    );
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Master Super Admin */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-indigo-400" /> Super Admin GENIA
            </span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Panel <span className="bg-gradient-to-r from-[#4f46e5] via-[#6366f1] to-[#38bdf8] bg-clip-text text-transparent">Master</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Control centralizado de subcuentas, asignación de capas modulares y supervisión de agentes.
          </p>
        </div>

        {/* Acciones Rápidas */}
        <div className="flex items-center gap-2">
          <Link
            href="/agents"
            className="flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-500/20 transition cursor-pointer"
          >
            <Bot className="w-4 h-4" />
            <span>Configurar Agentes & LLM</span>
          </Link>

          <Link
            href="/users"
            className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-white/[0.08] transition cursor-pointer"
          >
            <UserCheck className="w-4 h-4 text-emerald-400" />
            <span>Aprobar Usuarios</span>
          </Link>
        </div>
      </div>

      {/* Tarjetas de Métricas Globales */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0b0f19] border border-white/[0.08] p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Subcuentas Clientes</span>
          <p className="text-2xl font-black text-white">{subaccounts.length}</p>
          <span className="text-[11px] text-emerald-400 font-medium">100% activas</span>
        </div>

        <div className="bg-[#0b0f19] border border-white/[0.08] p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Agentes Operando</span>
          <p className="text-2xl font-black text-cyan-300">{agents.length || 3}</p>
          <span className="text-[11px] text-slate-400">Vertex AI & Gemini 2.5</span>
        </div>

        <div className="bg-[#0b0f19] border border-white/[0.08] p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Ingresos Recurrentes (MRR)</span>
          <p className="text-2xl font-black text-emerald-400">$3.491.000 COP</p>
          <span className="text-[11px] text-slate-400">Planes activos en plataforma</span>
        </div>

        <div className="bg-[#0b0f19] border border-white/[0.08] p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Protección de IP (Prompts)</span>
          <p className="text-2xl font-black text-indigo-400 flex items-center gap-1.5">
            <Lock className="w-5 h-5" /> 100% Blindado
          </p>
          <span className="text-[11px] text-slate-400">Oculto a cuentas cliente</span>
        </div>
      </div>

      {/* Tabla de Subcuentas de Clientes y Asignador de Capas */}
      <div className="bg-[#0b0f19] border border-white/[0.08] rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" /> Subcuentas y Capas Asignadas
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Controla qué módulos ve cada cliente activando o cambiando su capa.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#070a12]/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-white/[0.08]">
              <tr>
                <th className="py-3.5 px-4">Cliente / Empresa</th>
                <th className="py-3.5 px-4">Sector</th>
                <th className="py-3.5 px-4">Capa Activa (Plan)</th>
                <th className="py-3.5 px-4">Canales Activos</th>
                <th className="py-3.5 px-4">Agente Vinculado</th>
                <th className="py-3.5 px-4 text-right">Gestión</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06]">
              {subaccounts.map((sub) => (
                <tr key={sub.id} className="hover:bg-slate-800/20 transition-colors">
                  <td className="py-3.5 px-4 font-bold text-white">
                    {sub.name}
                  </td>

                  <td className="py-3.5 px-4 text-slate-400">
                    {sub.industry}
                  </td>

                  <td className="py-3.5 px-4">
                    <select
                      value={sub.tier}
                      onChange={(e) => handleUpdateTier(sub.id, e.target.value as any)}
                      className="bg-[#070a12] border border-white/[0.1] text-xs text-white rounded-lg px-2.5 py-1 focus:outline-none focus:border-indigo-500 cursor-pointer font-semibold"
                    >
                      <option value="esencial">🟢 Esencial ($197K)</option>
                      <option value="pro">🔵 Profesional ($497K)</option>
                      <option value="business">🟣 Business ($997K)</option>
                      <option value="enterprise">🟠 Enterprise ($1.997K)</option>
                    </select>
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="flex flex-wrap gap-1">
                      {sub.channels.map((ch) => (
                        <span
                          key={ch}
                          className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                        >
                          {ch}
                        </span>
                      ))}
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <span className="text-cyan-300 font-medium flex items-center gap-1">
                      <Bot className="w-3.5 h-3.5 text-indigo-400" />
                      {sub.assignedAgentName}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <Link
                      href={`/agents/${sub.agentId}`}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium text-[11px] transition"
                    >
                      <Settings className="w-3 h-3" />
                      <span>Configurar IA</span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
