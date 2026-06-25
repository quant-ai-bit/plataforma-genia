"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useAppContext } from "../../../lib/AppContext";
import { authenticatedFetch } from "../../../lib/api";
import { DashboardMetrics } from "../../../lib/types";
import {
  Bot,
  MessageSquare,
  UserCheck,
  Layers,
  TrendingUp
} from "lucide-react";

export default function DashboardPage() {
  const { isBackendOnline, agents } = useAppContext();
  const [loading, setLoading] = useState<boolean>(true);
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    total_agents: 0,
    total_conversations: 0,
    total_leads: 0,
    conversations_by_status: { active: 0, handoff: 0, closed: 0 },
    leads_history: [],
    recent_leads: [],
    recent_conversations: []
  });

  const parseBackendDate = (dateStr: string) => {
    try {
      return new Date(dateStr);
    } catch {
      return new Date();
    }
  };

  const loadData = async () => {
    setLoading(true);
    if (isBackendOnline) {
      try {
        const res = await authenticatedFetch(`/api/dashboard/metrics`);
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        } else {
          throw new Error("Failed to fetch metrics");
        }
      } catch (err) {
        console.error("Error al cargar métricas del backend:", err);
        loadMockMetrics();
      }
    } else {
      loadMockMetrics();
    }
    setLoading(false);
  };

  const loadMockMetrics = () => {
    setMetrics({
      total_agents: agents.length || 2,
      total_conversations: 24,
      total_leads: 7,
      conversations_by_status: { active: 3, handoff: 2, closed: 19 },
      leads_history: [
        { date: "2026-06-03", leads: 0 },
        { date: "2026-06-04", leads: 1 },
        { date: "2026-06-05", leads: 2 },
        { date: "2026-06-06", leads: 0 },
        { date: "2026-06-07", leads: 1 },
        { date: "2026-06-08", leads: 3 },
        { date: "2026-06-09", leads: 7 }
      ],
      recent_leads: [
        { name: "Juan Pérez", email: "juan@perez.com", phone: "+573001234567", agent_name: "Genia Agente Inmobiliario", source_channel: "web", captured_at: new Date().toISOString() },
        { name: "María Gómez", email: "maria@gomez.com", phone: "+34600123456", agent_name: "Genia Agente Inmobiliario", source_channel: "web", captured_at: new Date().toISOString() }
      ],
      recent_conversations: [
        { contact_name: "Juan Pérez", status: "active", last_message: "Quiero ver el apartamento de 3 habitaciones.", agent_name: "Genia Agente Inmobiliario", last_message_at: new Date().toISOString() },
        { contact_name: "María Gómez", status: "handoff", last_message: "Necesito hablar con un humano por favor.", agent_name: "Genia Agente Inmobiliario", last_message_at: new Date().toISOString() },
        { contact_name: "Carlos Soto", status: "closed", last_message: "Gracias por la información.", agent_name: "Genia Asistente Soporte TI", last_message_at: new Date().toISOString() }
      ]
    });
  };

  useEffect(() => {
    if (isBackendOnline !== null) {
      loadData();
    }
  }, [isBackendOnline, agents]);

  const conversionRate = metrics.total_conversations > 0 
    ? Math.round((metrics.total_leads / metrics.total_conversations) * 100)
    : 0;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Tarjetas de Métricas Principales */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Agentes Totales */}
        <Link 
          href="/agents"
          className="glow-card p-6 rounded-2xl flex items-center justify-between cursor-pointer hover:border-blue-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all duration-250 group"
          title="Administrar agentes"
        >
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider group-hover:text-blue-400 transition-colors">Agentes Operando</p>
            <p className="text-3xl font-extrabold text-white mt-2">{metrics.total_agents}</p>
            <p className="text-[10px] text-gray-500 mt-1">Configurados y activos</p>
          </div>
          <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/15 group-hover:bg-blue-500/20 group-hover:scale-110 transition-all duration-250">
            <Bot className="w-6 h-6" />
          </div>
        </Link>

        {/* Chats Totales */}
        <Link 
          href="/conversations"
          className="glow-card p-6 rounded-2xl flex items-center justify-between cursor-pointer hover:border-purple-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all duration-250 group"
          title="Ver listado completo de chats"
        >
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider group-hover:text-purple-400 transition-colors">Total de Chats</p>
            <p className="text-3xl font-extrabold text-white mt-2">{metrics.total_conversations}</p>
            <p className="text-[10px] text-gray-500 mt-1">Ver todas las sesiones registradas</p>
          </div>
          <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/15 group-hover:bg-purple-500/20 group-hover:scale-110 transition-all duration-250">
            <MessageSquare className="w-6 h-6 animate-pulse" />
          </div>
        </Link>

        {/* Leads Capturados */}
        <Link 
          href="/leads"
          className="glow-card p-6 rounded-2xl flex items-center justify-between cursor-pointer hover:border-green-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all duration-250 group"
          title="Ver todos los leads"
        >
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider group-hover:text-green-400 transition-colors">Leads Capturados</p>
            <p className="text-3xl font-extrabold text-green-400 mt-2">{metrics.total_leads}</p>
            <p className="text-[10px] text-gray-500 mt-1">Clientes potenciales guardados</p>
          </div>
          <div className="p-3 bg-green-500/10 text-green-400 rounded-xl border border-green-500/15 group-hover:bg-green-500/20 group-hover:scale-110 transition-all duration-250">
            <UserCheck className="w-6 h-6" />
          </div>
        </Link>

        {/* Tasa de Conversión */}
        <Link 
          href="/leads"
          className="glow-card p-6 rounded-2xl flex items-center justify-between cursor-pointer hover:border-indigo-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all duration-250 group"
          title="Ir a leads capturados"
        >
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider group-hover:text-indigo-400 transition-colors">Tasa de Captura</p>
            <p className="text-3xl font-extrabold text-indigo-400 mt-2">{conversionRate}%</p>
            <p className="text-[10px] text-gray-500 mt-1">Leads / conversaciones</p>
          </div>
          <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/15 group-hover:bg-indigo-500/20 group-hover:scale-110 transition-all duration-250">
            <Layers className="w-6 h-6" />
          </div>
        </Link>

      </div>

      {/* Contenido en dos columnas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Columna Izquierda: Gráfica e Historial de Leads */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glow-card p-6 rounded-2xl">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-bold text-white">Tendencia de Captura (Últimos 7 Días)</h3>
            </div>
            
            {/* Gráfica básica estilizada usando CSS Flex */}
            <div className="h-64 flex items-end justify-between gap-2 pt-6">
              {metrics.leads_history && metrics.leads_history.map((day: any, idx: number) => {
                const maxLeads = Math.max(...metrics.leads_history.map((h: any) => h.leads), 1);
                const percentHeight = (day.leads / maxLeads) * 90; // max 90%
                
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center group">
                    <div className="text-[10px] text-gray-400 mb-1 opacity-0 group-hover:opacity-100 transition duration-200">
                      {day.leads}
                    </div>
                    <div 
                      className="w-full bg-gradient-to-t from-blue-600 via-indigo-500 to-purple-500 rounded-t-lg transition-all duration-500 ease-out min-h-[4px]"
                      style={{ height: `${percentHeight || 5}%` }}
                    ></div>
                    <div className="text-[10px] text-gray-500 mt-2 text-center select-none truncate w-full">
                      {day.date.split("-").slice(1).reverse().join("/")}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Leads Recientes */}
          <div className="glow-card p-6 rounded-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Leads Capturados Recientemente</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-[#1e293b] text-gray-400 text-xs font-semibold uppercase">
                    <th className="pb-3">Nombre</th>
                    <th className="pb-3">Email / Teléfono</th>
                    <th className="pb-3">Agente Capturador</th>
                    <th className="pb-3">Canal</th>
                    <th className="pb-3 text-right">Fecha</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e293b] text-sm">
                  {metrics.recent_leads && metrics.recent_leads.length > 0 ? (
                    metrics.recent_leads.map((lead: any, idx: number) => (
                      <tr key={idx} className="hover:bg-gray-800/20 transition-colors">
                        <td className="py-3 font-semibold text-blue-300">{lead.name || "Sin nombre"}</td>
                        <td className="py-3 text-gray-300">
                          <p>{lead.email || "No provisto"}</p>
                          <p className="text-xs text-gray-500">{lead.phone || ""}</p>
                        </td>
                        <td className="py-3 text-gray-400">{lead.agent_name || "Agente"}</td>
                        <td className="py-3">
                          <span className="px-2 py-0.5 bg-gray-850 rounded-full border border-gray-700 text-xs uppercase text-gray-300">
                            {lead.source_channel}
                          </span>
                        </td>
                        <td className="py-3 text-right text-gray-500 text-xs">
                          {parseBackendDate(lead.captured_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-4 text-center text-gray-500">
                        No se han capturado leads en las conversaciones recientes.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Columna Derecha: Estado de Chats y Conversaciones Recientes */}
        <div className="space-y-6">
          
          {/* Distribución por Estados */}
          <div className="glow-card p-6 rounded-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Estado de las Conversaciones</h3>
            <div className="space-y-4">
              {/* Chats Activos */}
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-blue-400">En Curso (Activos)</span>
                  <span className="text-white">{metrics.conversations_by_status.active}</span>
                </div>
                <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-blue-500 h-full rounded-full" 
                    style={{ 
                      width: `${(metrics.conversations_by_status.active / (metrics.total_conversations || 1)) * 100}%` 
                    }}
                  ></div>
                </div>
              </div>
              
              {/* Derivados a Humanos */}
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-purple-400">Derivados (Handoff)</span>
                  <span className="text-white">{metrics.conversations_by_status.handoff}</span>
                </div>
                <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-purple-500 h-full rounded-full" 
                    style={{ 
                      width: `${(metrics.conversations_by_status.handoff / (metrics.total_conversations || 1)) * 100}%` 
                    }}
                  ></div>
                </div>
              </div>

              {/* Cerrados */}
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-gray-400">Finalizados (Cerrados)</span>
                  <span className="text-white">{metrics.conversations_by_status.closed}</span>
                </div>
                <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-gray-600 h-full rounded-full" 
                    style={{ 
                      width: `${(metrics.conversations_by_status.closed / (metrics.total_conversations || 1)) * 100}%` 
                    }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          {/* Conversaciones Recientes */}
          <div className="glow-card p-6 rounded-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Últimos Chats</h3>
            <div className="space-y-4">
              {metrics.recent_conversations && metrics.recent_conversations.length > 0 ? (
                metrics.recent_conversations.map((conv: any, idx: number) => (
                  <div key={idx} className="p-3 bg-gray-900/40 border border-gray-800 rounded-xl hover:border-gray-700 transition">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-gray-200">{conv.contact_name}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        conv.status === "active" 
                          ? "bg-green-950/60 border border-green-500/20 text-green-400" 
                          : conv.status === "handoff" 
                          ? "bg-purple-950/60 border border-purple-500/20 text-purple-400" 
                          : "bg-gray-850 border border-gray-700 text-gray-400"
                      }`}>
                        {conv.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1.5 italic truncate">"{conv.last_message}"</p>
                    <div className="flex items-center justify-between text-[10px] text-gray-500 mt-2 font-semibold">
                      <span>Asignado a: {conv.agent_name}</span>
                      <span>{parseBackendDate(conv.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-gray-550 text-center py-4">No hay conversaciones recientes.</p>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
