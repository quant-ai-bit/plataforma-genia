"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "../../../lib/AppContext";
import { authenticatedFetch } from "../../../lib/api";
import { Agent } from "../../lib/types";
import {
  Bot,
  Plus,
  Settings,
  Trash2,
  Sparkles,
  X,
  ChevronDown,
  ChevronRight
} from "lucide-react";

export default function AgentsPage() {
  const router = useRouter();
  const {
    agents,
    setAgents,
    isBackendOnline,
    availableModels,
    agentUsages,
    loadBackendData
  } = useAppContext();

  // Modal State for New Agent
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);

  // Form State
  const [form, setForm] = useState({
    name: "",
    description: "",
    system_prompt: "",
    provider: "groq",
    model: "llama-3.3-70b-versatile",
    temperature: 0.7,
    max_tokens: 1024
  });

  // Expanded Usages
  const [expandedUsageId, setExpandedUsageId] = useState<string | null>(null);

  const resetForm = () => {
    setForm({
      name: "",
      description: "",
      system_prompt: "",
      provider: "groq",
      model: "llama-3.3-70b-versatile",
      temperature: 0.7,
      max_tokens: 1024
    });
  };

  const handleProviderChange = (provider: string) => {
    let defaultModel = "llama-3.3-70b-versatile";
    if (provider === "gemini") {
      defaultModel = "gemini-2.5-flash";
    } else if (provider === "openrouter") {
      defaultModel = "deepseek/deepseek-chat";
    }
    setForm(prev => ({ ...prev, provider, model: defaultModel }));
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.system_prompt.trim()) return;

    setSubmitLoading(true);
    const payload = {
      name: form.name,
      description: form.description || null,
      system_prompt: form.system_prompt,
      provider: form.provider,
      model: form.model,
      temperature: form.temperature,
      max_tokens: form.max_tokens,
      custom_fields: [],
      channels: ["web"],
      notification_phone: null
    };

    if (!isBackendOnline) {
      // Simulación local
      const mockId = `mock-${Date.now()}`;
      const newAgent: Agent = {
        ...payload,
        id: mockId,
        created_at: new Date().toISOString()
      };
      setAgents(prev => [newAgent, ...prev]);
      setIsModalOpen(false);
      resetForm();
      setSubmitLoading(false);
      router.push(`/agents/${mockId}`);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/agents/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const createdAgent = await res.json();
        await loadBackendData();
        setIsModalOpen(false);
        resetForm();
        router.push(`/agents/${createdAgent.id}`);
      } else {
        const data = await res.json();
        alert(`Error al guardar agente: ${JSON.stringify(data.detail)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al guardar agente.");
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleDeleteAgent = async (agentId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("¿Estás seguro de eliminar este agente y todos sus datos relacionados (chats, leads)?")) return;

    if (!isBackendOnline) {
      setAgents(prev => prev.filter(a => a.id !== agentId));
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/agents/${agentId}`, { method: "DELETE" });
      if (res.ok) {
        await loadBackendData();
      } else {
        alert("No se pudo eliminar el agente.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Get active models list based on provider in form
  const currentProviderModels = 
    form.provider === "groq"
      ? availableModels.groq || []
      : form.provider === "gemini"
      ? availableModels.gemini || []
      : availableModels.openrouter || [];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Title section with create button */}
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-bold text-white">Agentes Activos</h3>
          <p className="text-xs text-gray-400 mt-1">
            Lista de asistentes configurados en la plataforma.
          </p>
        </div>
        <button
          onClick={() => {
            resetForm();
            setIsModalOpen(true);
          }}
          className="flex items-center gap-1.5 py-2.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs rounded-xl font-bold border border-blue-500/20 shadow-lg shadow-blue-500/15 transition cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          Crear Agente
        </button>
      </div>

      {/* Grid of Agents */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* Card of New Agent */}
        <button
          onClick={() => {
            resetForm();
            setIsModalOpen(true);
          }}
          className="min-h-[220px] border-2 border-dashed border-gray-800 hover:border-blue-500/30 rounded-2xl flex flex-col items-center justify-center gap-3 text-gray-500 hover:text-blue-400 transition-all duration-300 group hover:bg-blue-500/5 cursor-pointer"
        >
          <div className="w-14 h-14 rounded-2xl bg-gray-800/50 group-hover:bg-blue-500/10 flex items-center justify-center transition-all">
            <Plus className="w-7 h-7" />
          </div>
          <span className="text-sm font-semibold">Crear Nuevo Agente</span>
        </button>

        {agents.map((agent) => {
          const usages = agentUsages[agent.id] || [];
          const totalCost = usages.reduce((sum, u) => sum + (u.cost || 0), 0);
          const totalTokens = usages.reduce((sum, u) => sum + (u.total_tokens || 0), 0);

          return (
            <div
              key={agent.id}
              onClick={() => router.push(`/agents/${agent.id}`)}
              className="glow-card rounded-2xl p-6 flex flex-col justify-between border border-gray-800 hover:border-blue-500/20 cursor-pointer hover:shadow-[0_0_20px_rgba(59,130,246,0.15)] transition duration-300 relative group"
            >
              <div>
                {/* Header card info */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <h4 className="font-bold text-white group-hover:text-blue-400 transition-colors text-sm truncate">
                      {agent.name}
                    </h4>
                    <p className="text-[11px] text-gray-550 truncate mt-0.5">
                      {agent.description || "Sin descripción"}
                    </p>
                  </div>
                  <div className="p-2 bg-blue-500/5 text-blue-400 rounded-lg border border-blue-500/10 flex-shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                </div>

                {/* Badge specifications */}
                <div className="flex flex-wrap gap-2 mt-4">
                  <span className="px-2 py-0.5 bg-gray-850 border border-gray-700 text-[10px] text-gray-400 rounded-lg font-bold">
                    {agent.provider.toUpperCase()}
                  </span>
                  <span className="px-2 py-0.5 bg-gray-850 border border-gray-700 text-[10px] text-gray-400 rounded-lg font-bold truncate max-w-[140px]" title={agent.model}>
                    {agent.model}
                  </span>
                </div>

                {/* Usage metrics summary */}
                <div className="mt-5 space-y-2 border-t border-gray-850/60 pt-4">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500 font-semibold">Tokens Usados</span>
                    <span className="text-gray-300 font-mono font-bold">
                      {totalTokens.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500 font-semibold">Costo Total</span>
                    <span className="text-green-400 font-mono font-bold">
                      ${totalCost.toFixed(4)}
                    </span>
                  </div>

                  {usages.length > 0 && (
                    <div className="mt-2 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedUsageId(expandedUsageId === agent.id ? null : agent.id);
                        }}
                        className="text-[10px] text-blue-400 hover:underline flex items-center justify-end gap-1 ml-auto font-semibold"
                      >
                        <span>{expandedUsageId === agent.id ? "Ocultar desglose" : "Ver desglose por modelo"}</span>
                      </button>
                    </div>
                  )}

                  {expandedUsageId === agent.id && usages.length > 0 && (
                    <div className="mt-3 p-3 bg-[#0d1321]/50 border border-gray-850 rounded-xl space-y-1.5 animate-fadeIn">
                      {usages.map((u: any) => (
                        <div key={u.id} className="flex justify-between items-center text-[10px] text-gray-300">
                          <span className="font-mono text-gray-400 truncate max-w-[120px]" title={u.model}>
                            {u.model}
                          </span>
                          <div className="flex gap-2 font-semibold">
                            <span className="font-mono">{u.total_tokens.toLocaleString()} t</span>
                            <span className="font-mono text-green-400 font-bold">${u.cost.toFixed(6)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex gap-3 border-t border-gray-850 pt-4 mt-6">
                <button
                  type="button"
                  onClick={() => router.push(`/agents/${agent.id}`)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-gray-800 hover:bg-blue-600/20 hover:border-blue-500/30 text-gray-300 hover:text-blue-300 text-xs rounded-xl font-semibold border border-gray-700 transition cursor-pointer"
                >
                  <Settings className="w-3.5 h-3.5" />
                  Configurar
                </button>
                <button
                  type="button"
                  onClick={(e) => handleDeleteAgent(agent.id, e)}
                  className="flex items-center justify-center p-2 bg-red-950/20 hover:bg-red-900/30 text-red-400 text-xs rounded-xl border border-red-500/10 hover:border-red-500/20 transition cursor-pointer"
                  title="Eliminar agente"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}

      </div>

      {/* Sleek Modal for New Agent */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-[#070b13]/80 backdrop-filter backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="glow-card max-w-xl w-full rounded-2xl p-6 relative flex flex-col max-h-[90vh] bg-[#0c101c]/95 border border-gray-800">
            {/* Close button */}
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 p-1.5 hover:bg-gray-800 rounded-xl transition text-gray-400 hover:text-white cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            {/* Header */}
            <div className="flex items-center gap-3 border-b border-gray-800 pb-4 mb-4">
              <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/20">
                <Sparkles className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h4 className="text-md font-bold text-white">Crear Agente Nuevo</h4>
                <p className="text-xs text-gray-400 mt-0.5">Introduce los parámetros iniciales de tu agente de IA.</p>
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleCreateAgent} className="flex-1 overflow-y-auto space-y-4 pr-1 text-xs">
              
              {/* General Info */}
              <div className="space-y-3 p-4 bg-gray-900/20 border border-gray-800 rounded-xl">
                <h5 className="font-bold text-white text-xs">Información Básica</h5>
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Nombre del Agente *</label>
                  <input
                    type="text"
                    required
                    value={form.name}
                    onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Ej. Ventas Inmobiliarias o Bot de Soporte"
                    className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Descripción</label>
                  <input
                    type="text"
                    value={form.description}
                    onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Ej. Asistente encargado de capturar y validar datos"
                    className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                  />
                </div>
              </div>

              {/* LLM Config */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-900/20 border border-gray-800 rounded-xl">
                <h5 className="font-bold text-white text-xs col-span-full">Configuración del LLM</h5>
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Proveedor LLM</label>
                  <select
                    value={form.provider}
                    onChange={e => handleProviderChange(e.target.value)}
                    className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none font-semibold"
                  >
                    <option value="groq">Groq (Chat LLM)</option>
                    <option value="gemini">Gemini (Utility LLM)</option>
                    <option value="openrouter">OpenRouter (Multi-LLM)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Modelo LLM</label>
                  <select
                    value={form.model}
                    onChange={e => setForm(prev => ({ ...prev, model: e.target.value }))}
                    className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none font-semibold"
                  >
                    {currentProviderModels.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                    {currentProviderModels.length === 0 && (
                      <option value={form.model}>{form.model}</option>
                    )}
                  </select>
                </div>
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Temperatura: {form.temperature}</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={form.temperature}
                    onChange={e => setForm(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                    className="w-full accent-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Max Tokens</label>
                  <input
                    type="number"
                    min="1"
                    max="4096"
                    value={form.max_tokens}
                    onChange={e => setForm(prev => ({ ...prev, max_tokens: parseInt(e.target.value) || 1024 }))}
                    className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                  />
                </div>
              </div>

              {/* System Prompt */}
              <div className="space-y-3 p-4 bg-gray-900/20 border border-gray-800 rounded-xl">
                <h5 className="font-bold text-white text-xs">Instrucciones del Sistema *</h5>
                <div>
                  <textarea
                    required
                    value={form.system_prompt}
                    onChange={e => setForm(prev => ({ ...prev, system_prompt: e.target.value }))}
                    placeholder="Instrucciones detalladas de comportamiento y contexto..."
                    rows={4}
                    className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none resize-none"
                  />
                </div>
              </div>

              {/* Submit Buttons */}
              <div className="flex gap-4 border-t border-gray-850 pt-4 mt-auto">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-2.5 bg-gray-800 hover:bg-gray-750 text-gray-300 rounded-xl font-bold border border-gray-700 transition cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitLoading || !form.name.trim() || !form.system_prompt.trim()}
                  className="flex-1 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold shadow-lg transition cursor-pointer"
                >
                  {submitLoading ? "Guardando..." : "Crear Agente"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
