"use client";

import React, { useState, useEffect } from "react";
import { 
  FileSpreadsheet, 
  Download, 
  ShieldCheck, 
  RefreshCw, 
  Calendar, 
  Terminal,
  Activity,
  Bot,
  Database,
  ArrowRight,
  Globe
} from "lucide-react";
import { authenticatedFetch } from "../../../lib/api";

export default function EvidencePage() {
  const [lang, setLang] = useState<"es" | "en">("es");
  const [loading, setLoading] = useState<boolean>(true);
  const [exportLoading, setExportLoading] = useState<boolean>(false);
  const [summary, setSummary] = useState<any>({
    agents: 0,
    conversations: 0,
    leads: 0,
    tokens: { total: 0 },
    actions_executed: 0
  });
  const [logs, setLogs] = useState<any[]>([]);

  // Export Form States
  const [fromDate, setFromDate] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [toDate, setToDate] = useState<string>(() => {
    return new Date().toISOString().split("T")[0];
  });
  const [exportFormat, setExportFormat] = useState<"json" | "csv">("json");

  const loadData = async () => {
    setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      
      // Fetch Summary
      const summaryRes = await fetch(`${baseUrl}/api/metrics/summary`);
      if (summaryRes.ok) {
        const summaryData = await summaryRes.json();
        setSummary(summaryData);
      }

      // Fetch Recent Logs
      const logsRes = await fetch(`${baseUrl}/api/metrics/logs`);
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setLogs(logsData);
      }
    } catch (err) {
      console.error("Error loading evidence data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleExport = async (e: React.FormEvent) => {
    e.preventDefault();
    setExportLoading(true);
    try {
      const queryParams = new URLSearchParams({
        from: fromDate,
        to: toDate,
        format: exportFormat
      });
      
      const res = await authenticatedFetch(`/v1/admin/evidence-export?${queryParams.toString()}`);
      if (res.ok) {
        // Handle file download
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `evidence_export_${fromDate}_to_${toDate}.${exportFormat}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        alert(lang === "es" ? "Error al exportar evidencia. Verifique los permisos." : "Error exporting evidence. Verify permissions.");
      }
    } catch (err) {
      console.error("Export error:", err);
      alert(lang === "es" ? "Error de conexión al exportar." : "Connection error while exporting.");
    } finally {
      setExportLoading(false);
    }
  };

  const t = {
    es: {
      title: "Evidencia de Producto y Logs",
      subtitle: "Registro de auditoría de agentes de IA, logs de MCP y exportador de evidencias para jueces del hackathon.",
      statsTitle: "Estadísticas del Sistema",
      metricAgents: "Agentes Activos",
      metricConvs: "Chats Totales",
      metricLeads: "Leads Capturados",
      metricActions: "Acciones MCP",
      metricTokens: "Tokens de IA",
      exportTitle: "Exportador de Evidencia Oficial (XPRIZE)",
      exportFrom: "Fecha de Inicio:",
      exportTo: "Fecha de Fin:",
      exportFormat: "Formato:",
      exportBtn: "Descargar Paquete de Evidencia",
      logsTitle: "Auditoría en Tiempo Real (Ejecuciones MCP)",
      logsSubtitle: "Logs recientes de herramientas invocadas por los agentes.",
      colDate: "Fecha y Hora",
      colTool: "Herramienta",
      colProvider: "Modelo Provider",
      colStatus: "Estado",
      emptyLogs: "No se registran logs de acciones en el sistema."
    },
    en: {
      title: "Product Evidence & Logs",
      subtitle: "AI Agent audit trail, MCP logs, and official evidence exporter for hackathon judges.",
      statsTitle: "System Statistics",
      metricAgents: "Active Agents",
      metricConvs: "Total Conversations",
      metricLeads: "Captured Leads",
      metricActions: "MCP Actions",
      metricTokens: "IA Tokens",
      exportTitle: "Official Evidence Exporter (XPRIZE)",
      exportFrom: "Start Date:",
      exportTo: "End Date:",
      exportFormat: "Format:",
      exportBtn: "Download Evidence Package",
      logsTitle: "Real-time Audit Trail (MCP Executions)",
      logsSubtitle: "Recent tool execution logs triggered by AI agents.",
      colDate: "Date & Time",
      colTool: "Tool",
      colProvider: "Model Provider",
      colStatus: "Status",
      emptyLogs: "No action logs registered in the system."
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 animate-fadeIn text-xs">
      
      {/* HEADER CONTROL */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gray-900/10 border border-gray-850 p-6 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/15">
            <ShieldCheck className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">{t[lang].title}</h3>
            <p className="text-[10px] text-gray-500">{t[lang].subtitle}</p>
          </div>
        </div>

        <div className="flex gap-2">
          <button 
            onClick={loadData}
            className="p-2 text-gray-400 hover:text-white bg-gray-800/40 hover:bg-gray-800 border border-gray-700 rounded-xl transition"
            title="Sincronizar"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          
          <button 
            onClick={() => setLang(lang === "es" ? "en" : "es")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl text-[10px] font-semibold text-white transition cursor-pointer"
          >
            <Globe className="w-3.5 h-3.5 text-blue-400" />
            <span>{lang === "es" ? "English" : "Español"}</span>
          </button>
        </div>
      </div>

      {/* SYSTEM STATS SUMMARY */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-[#0c101c]/40 border border-gray-850 p-4 rounded-xl flex items-center gap-3">
          <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-lg">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase">{t[lang].metricAgents}</p>
            <p className="text-lg font-extrabold text-white mt-0.5">{summary.agents}</p>
          </div>
        </div>

        <div className="bg-[#0c101c]/40 border border-gray-850 p-4 rounded-xl flex items-center gap-3">
          <div className="p-2.5 bg-purple-500/10 text-purple-400 rounded-lg">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase">{t[lang].metricConvs}</p>
            <p className="text-lg font-extrabold text-white mt-0.5">{summary.conversations}</p>
          </div>
        </div>

        <div className="bg-[#0c101c]/40 border border-gray-850 p-4 rounded-xl flex items-center gap-3">
          <div className="p-2.5 bg-green-500/10 text-green-400 rounded-lg">
            <UserCheck className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase">{t[lang].metricLeads}</p>
            <p className="text-lg font-extrabold text-green-400 mt-0.5">{summary.leads}</p>
          </div>
        </div>

        <div className="bg-[#0c101c]/40 border border-gray-850 p-4 rounded-xl flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-lg">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase">{t[lang].metricActions}</p>
            <p className="text-lg font-extrabold text-white mt-0.5">{summary.actions_executed || 0}</p>
          </div>
        </div>

        <div className="bg-[#0c101c]/40 border border-gray-850 p-4 rounded-xl flex items-center gap-3 col-span-2 md:col-span-1">
          <div className="p-2.5 bg-indigo-500/10 text-indigo-400 rounded-lg">
            <Database className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <p className="text-[10px] text-gray-500 uppercase">{t[lang].metricTokens}</p>
            <p className="text-sm font-extrabold text-white mt-0.5 truncate">
              {(summary.tokens?.total || 0).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* ACTION LOGS AUDIT TRAIL */}
        <div className="lg:col-span-2 glow-card rounded-2xl overflow-hidden border border-gray-850 p-6 space-y-4">
          <div>
            <h4 className="text-sm font-bold text-white">{t[lang].logsTitle}</h4>
            <p className="text-[10px] text-gray-500">{t[lang].logsSubtitle}</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-850 text-gray-400 font-semibold uppercase bg-gray-900/10">
                  <th className="py-2.5 px-3">{t[lang].colDate}</th>
                  <th className="py-2.5 px-3">{t[lang].colTool}</th>
                  <th className="py-2.5 px-3">{t[lang].colProvider}</th>
                  <th className="py-2.5 px-3 text-right">{t[lang].colStatus}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-850 text-[10px]">
                {logs.length > 0 ? (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-850/10 transition-colors">
                      <td className="py-2.5 px-3 text-gray-400">
                        {new Date(log.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-blue-300">
                        <span className="flex items-center gap-1.5">
                          <Terminal className="w-3 h-3 text-gray-500" />
                          {log.tool_name}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-gray-400 uppercase">
                        {log.model_provider}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                          log.status === "success" 
                            ? "bg-green-950/60 border border-green-500/20 text-green-400" 
                            : "bg-red-950/60 border border-red-500/20 text-red-400"
                        }`}>
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-gray-500">
                      {t[lang].emptyLogs}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* EXPORT COMPONENT */}
        <div className="glow-card rounded-2xl border border-gray-850 p-6 space-y-6">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-blue-400" />
            <h4 className="text-sm font-bold text-white">{t[lang].exportTitle}</h4>
          </div>

          <form onSubmit={handleExport} className="space-y-4">
            <div className="space-y-1">
              <label className="text-[10px] text-gray-400 font-semibold">{t[lang].exportFrom}</label>
              <div className="flex items-center gap-2 bg-[#0c101c] border border-gray-800 rounded-xl px-3 py-2 text-white">
                <Calendar className="w-3.5 h-3.5 text-gray-500" />
                <input 
                  type="date" 
                  value={fromDate}
                  onChange={e => setFromDate(e.target.value)}
                  className="w-full bg-transparent focus:outline-none text-xs" 
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-gray-400 font-semibold">{t[lang].exportTo}</label>
              <div className="flex items-center gap-2 bg-[#0c101c] border border-gray-800 rounded-xl px-3 py-2 text-white">
                <Calendar className="w-3.5 h-3.5 text-gray-500" />
                <input 
                  type="date" 
                  value={toDate}
                  onChange={e => setToDate(e.target.value)}
                  className="w-full bg-transparent focus:outline-none text-xs" 
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] text-gray-400 font-semibold">{t[lang].exportFormat}</label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setExportFormat("json")}
                  className={`py-2 px-3 rounded-xl border text-center font-bold transition cursor-pointer ${
                    exportFormat === "json"
                      ? "bg-blue-600/10 border-blue-500 text-blue-400"
                      : "bg-gray-900 border-gray-800 text-gray-400 hover:bg-gray-850"
                  }`}
                >
                  JSON
                </button>
                <button
                  type="button"
                  onClick={() => setExportFormat("csv")}
                  className={`py-2 px-3 rounded-xl border text-center font-bold transition cursor-pointer ${
                    exportFormat === "csv"
                      ? "bg-blue-600/10 border-blue-500 text-blue-400"
                      : "bg-gray-900 border-gray-800 text-gray-400 hover:bg-gray-850"
                  }`}
                >
                  CSV
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={exportLoading}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-xl shadow-lg shadow-blue-500/10 hover:shadow-blue-500/20 disabled:opacity-50 transition cursor-pointer"
            >
              {exportLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              <span>{t[lang].exportBtn}</span>
            </button>
          </form>
        </div>

      </div>

    </div>
  );
}
