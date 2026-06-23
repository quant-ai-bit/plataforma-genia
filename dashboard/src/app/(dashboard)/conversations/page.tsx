"use client";

import { useState, useEffect } from "react";
import { useAppContext } from "../../../lib/AppContext";
import { authenticatedFetch } from "../../../lib/api";
import { Conversation, Message } from "../../lib/types";
import {
  MessageSquare,
  Trash2,
  Eye,
  X,
  Loader2,
  RefreshCw,
  AlertTriangle,
  FolderOpen
} from "lucide-react";

export default function ConversationsPage() {
  const {
    agents,
    isBackendOnline,
    loadBackendData
  } = useAppContext();

  // Conversations Lists
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [filterAgent, setFilterAgent] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");

  // Transcript Modal State
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<{
    id: string;
    contact_name: string;
    status: string;
    messages: Message[];
  } | null>(null);
  const [loadingTranscript, setLoadingTranscript] = useState<boolean>(false);

  const parseBackendDate = (dateStr: string) => {
    try {
      return new Date(dateStr);
    } catch {
      return new Date();
    }
  };

  const loadConversations = async () => {
    setLoading(true);
    if (!isBackendOnline) {
      // Mock conversations list
      setConversations([
        {
          id: "conv-1",
          agent_id: "agent-1",
          agent: { name: "Genia Agente Inmobiliario" },
          contact_name: "Juan Pérez",
          contact_phone: "+573001234567",
          status: "active",
          channel: "web",
          message_count: 8,
          last_message_at: new Date(Date.now() - 600000).toISOString(),
          started_at: new Date(Date.now() - 3600000).toISOString()
        },
        {
          id: "conv-2",
          agent_id: "agent-1",
          agent: { name: "Genia Agente Inmobiliario" },
          contact_name: "María Gómez",
          contact_phone: "+34600123456",
          status: "handoff",
          channel: "whatsapp",
          message_count: 15,
          last_message_at: new Date(Date.now() - 1800000).toISOString(),
          started_at: new Date(Date.now() - 7200000).toISOString()
        },
        {
          id: "conv-3",
          agent_id: "agent-2",
          agent: { name: "Genia Asistente Soporte TI" },
          contact_name: "Carlos Soto",
          contact_phone: null,
          status: "closed",
          channel: "web",
          message_count: 4,
          last_message_at: new Date(Date.now() - 86400000).toISOString(),
          started_at: new Date(Date.now() - 87000000).toISOString()
        }
      ]);
      setLoading(false);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/conversations/`);
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error("Error al cargar chats:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, [isBackendOnline]);

  const handleViewTranscript = async (convId: string) => {
    setSelectedConvId(convId);
    setLoadingTranscript(true);

    if (!isBackendOnline) {
      // Mock transcript
      setTimeout(() => {
        const matchingConv = conversations.find(c => c.id === convId);
        setTranscript({
          id: convId,
          contact_name: matchingConv?.contact_name || "Usuario de prueba",
          status: matchingConv?.status || "active",
          messages: [
            { id: "m-1", role: "user", content: "Hola, me interesa automatizar mis procesos.", sent_at: new Date(Date.now() - 3600000).toISOString() },
            { id: "m-2", role: "assistant", content: "¡Hola! Con gusto, ¿cuál es tu nombre y correo?", sent_at: new Date(Date.now() - 3500000).toISOString() },
            { id: "m-3", role: "user", content: "Me llamo Carlos Gómez, mi correo es carlos@inmobiliaria.xyz", sent_at: new Date(Date.now() - 3400000).toISOString() },
            { id: "m-4", role: "assistant", content: "¡Gracias Carlos! He registrado tus datos en la consola.", sent_at: new Date(Date.now() - 3300000).toISOString() }
          ]
        });
        setLoadingTranscript(false);
      }, 500);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/conversations/${convId}`);
      if (res.ok) {
        const data = await res.json();
        setTranscript(data);
      }
    } catch (err) {
      console.error("Error al cargar la transcripción del chat:", err);
    } finally {
      setLoadingTranscript(false);
    }
  };

  const handleUpdateStatus = async (convId: string, newStatus: string) => {
    if (!isBackendOnline) {
      setConversations(prev => prev.map(c => c.id === convId ? { ...c, status: newStatus } : c));
      if (transcript && transcript.id === convId) {
        setTranscript(prev => prev ? { ...prev, status: newStatus } : null);
      }
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/conversations/${convId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        await loadConversations();
        if (transcript && transcript.id === convId) {
          setTranscript(prev => prev ? { ...prev, status: newStatus } : null);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteConv = async (convId: string) => {
    if (!confirm("¿Estás seguro de eliminar esta conversación y todos sus mensajes?")) return;

    if (!isBackendOnline) {
      setConversations(prev => prev.filter(c => c.id !== convId));
      if (selectedConvId === convId) {
        setSelectedConvId(null);
        setTranscript(null);
      }
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/conversations/${convId}`, { method: "DELETE" });
      if (res.ok) {
        await loadConversations();
        await loadBackendData(); // update general metrics
        if (selectedConvId === convId) {
          setSelectedConvId(null);
          setTranscript(null);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Helper to parse markdown images in chat bubbles
  const renderMessageContent = (content: string) => {
    const imageRegex = /!\[(.*?)\]\((.*?)\)/g;
    const parts = [];
    let lastIndex = 0;
    let match;
    while ((match = imageRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(<span key={lastIndex}>{content.substring(lastIndex, match.index)}</span>);
      }
      const alt = match[1];
      const url = match[2];
      parts.push(
        <div key={match.index} className="my-2 p-1 bg-[#0d1321]/50 border border-gray-850 rounded-xl max-w-xs overflow-hidden">
          <img src={url} alt={alt} className="rounded-lg max-h-36 object-cover w-full" />
          <span className="text-[9px] text-gray-500 mt-0.5 block text-center italic">{alt}</span>
        </div>
      );
      lastIndex = imageRegex.lastIndex;
    }
    if (lastIndex < content.length) {
      parts.push(<span key={lastIndex}>{content.substring(lastIndex)}</span>);
    }
    return parts.length > 0 ? parts : content;
  };

  const filteredConversations = conversations
    .filter(c => !filterAgent || c.agent_id === filterAgent)
    .filter(c => !filterStatus || c.status === filterStatus);

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 animate-fadeIn text-xs">
      
      {/* Title section with reload */}
      <div className="flex justify-between items-center bg-gray-900/10 border border-gray-850 p-4 rounded-2xl">
        <div>
          <h3 className="text-sm font-bold text-white">Historial de Chats</h3>
          <p className="text-[10px] text-gray-500">Consulta los registros completos de conversaciones y handoffs.</p>
        </div>
        <button
          onClick={loadConversations}
          className="p-2 text-gray-400 hover:text-white bg-gray-800/40 hover:bg-gray-800 border border-gray-700 rounded-xl transition cursor-pointer"
          title="Recargar chats"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Filters Pane */}
      <div className="flex flex-wrap gap-4 bg-[#0c101c]/45 p-4 rounded-2xl border border-gray-850">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-[10px] text-gray-500 font-bold mb-1">Filtrar por Agente</label>
          <select
            value={filterAgent}
            onChange={e => setFilterAgent(e.target.value)}
            className="w-full bg-[#070b13] border border-gray-850 text-xs text-gray-300 rounded-xl px-3 py-2 focus:outline-none"
          >
            <option value="">Todos los agentes</option>
            {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="block text-[10px] text-gray-500 font-bold mb-1">Filtrar por Estado</label>
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="w-full bg-[#070b13] border border-gray-850 text-xs text-gray-300 rounded-xl px-3 py-2 focus:outline-none"
          >
            <option value="">Todos los estados</option>
            <option value="active">Activo</option>
            <option value="handoff">Handoff (Derivado)</option>
            <option value="closed">Cerrado</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="glow-card rounded-2xl overflow-hidden border border-gray-850">
        {loading ? (
          <div className="flex h-48 items-center justify-center">
            <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-850 text-gray-400 font-semibold uppercase bg-gray-900/30">
                  <th className="px-6 py-4">Usuario / Contacto</th>
                  <th className="px-6 py-4">Agente Asignado</th>
                  <th className="px-6 py-4">Canal</th>
                  <th className="px-6 py-4">Estado</th>
                  <th className="px-6 py-4">Mensajes</th>
                  <th className="px-6 py-4">Última Actividad</th>
                  <th className="px-6 py-4 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-850 text-[11px]">
                {filteredConversations.map((conv) => (
                  <tr key={conv.id} className="hover:bg-gray-850/20 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-bold text-gray-200">{conv.contact_name || "Usuario Web Anónimo"}</p>
                      <p className="text-[10px] text-gray-500">{conv.contact_phone || "Sin teléfono"}</p>
                    </td>
                    <td className="px-6 py-4 text-gray-300">
                      {conv.agent?.name || "Agente"}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-0.5 bg-gray-850 border border-gray-700 text-gray-400 rounded-full font-bold uppercase">
                        {conv.channel}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[9px] font-extrabold uppercase ${
                        conv.status === "active" 
                          ? "bg-green-950/60 border border-green-500/20 text-green-400" 
                          : conv.status === "handoff" 
                          ? "bg-purple-950/60 border border-purple-500/20 text-purple-400 animate-pulse" 
                          : "bg-gray-850 border border-gray-700 text-gray-400"
                      }`}>
                        {conv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-bold text-gray-200">
                      {conv.message_count}
                    </td>
                    <td className="px-6 py-4 text-gray-500">
                      {parseBackendDate(conv.last_message_at || conv.started_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleViewTranscript(conv.id)}
                          className="p-1.5 bg-blue-950/20 hover:bg-blue-900/30 text-blue-400 rounded-lg border border-blue-500/10 hover:border-blue-500/20 transition cursor-pointer"
                          title="Ver Transcripción"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteConv(conv.id)}
                          className="p-1.5 bg-red-950/20 hover:bg-red-900/30 text-red-400 rounded-lg border border-red-500/10 hover:border-red-500/20 transition cursor-pointer"
                          title="Eliminar Conversación"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredConversations.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-16 text-center text-gray-500">
                      <FolderOpen className="w-8 h-8 mx-auto text-gray-600 mb-2" />
                      <p className="font-semibold text-xs">No se encontraron conversaciones</p>
                      <p className="text-[10px] text-gray-550 mt-0.5">Interactúa con los agentes en el Sandbox para generar registros.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Transcript Detail Modal */}
      {selectedConvId && (
        <div className="fixed inset-0 bg-[#070b13]/85 backdrop-filter backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fadeIn text-xs">
          <div className="glow-card max-w-2xl w-full rounded-2xl p-6 relative flex flex-col max-h-[85vh] bg-[#0c101c]/95 border border-gray-800">
            {/* Close button */}
            <button
              onClick={() => {
                setSelectedConvId(null);
                setTranscript(null);
              }}
              className="absolute top-4 right-4 p-1.5 hover:bg-gray-800 rounded-xl transition text-gray-400 hover:text-white cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            {/* Header transcript info */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-800 pb-4 mb-4 pr-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/15">
                  <MessageSquare className="w-5 h-5 text-blue-400 animate-pulse" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">
                    Chat de {transcript?.contact_name || "Cargando..."}
                  </h4>
                  <span className="text-[9px] text-gray-500 font-semibold uppercase block mt-0.5">
                    Historial Completo
                  </span>
                </div>
              </div>

              {transcript && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 font-semibold text-[10px]">Estado:</span>
                  <select
                    value={transcript.status}
                    onChange={e => handleUpdateStatus(transcript.id, e.target.value)}
                    className="bg-[#070b13] border border-gray-800 text-[10px] text-gray-300 rounded-lg px-2 py-1 focus:outline-none font-bold"
                  >
                    <option value="active">Activo</option>
                    <option value="handoff">Handoff (Derivado)</option>
                    <option value="closed">Cerrado</option>
                  </select>
                </div>
              )}
            </div>

            {/* Messages Body */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1 min-h-0 py-2">
              {loadingTranscript ? (
                <div className="flex h-48 items-center justify-center">
                  <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                </div>
              ) : transcript?.messages && transcript.messages.length > 0 ? (
                transcript.messages.map((msg: Message) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm shadow-md leading-relaxed ${
                        msg.role === "user"
                          ? "bg-gradient-to-tr from-blue-600 to-indigo-600 text-white rounded-br-none"
                          : "bg-gray-800 text-gray-100 rounded-bl-none border border-gray-700/60"
                      }`}
                    >
                      <p>{renderMessageContent(msg.content)}</p>
                      <span className="text-[8px] text-gray-500 block text-right mt-1.5 font-mono font-semibold">
                        {parseBackendDate(msg.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-center text-gray-500 italic py-8">No hay mensajes en esta conversación.</p>
              )}
            </div>

            {/* Footer actions */}
            <div className="flex gap-4 border-t border-gray-800 pt-4 mt-4 flex-shrink-0">
              <button
                type="button"
                onClick={() => {
                  setSelectedConvId(null);
                  setTranscript(null);
                }}
                className="flex-1 py-2 bg-gray-850 hover:bg-gray-800 text-gray-300 rounded-xl font-bold border border-gray-700 transition cursor-pointer"
              >
                Cerrar Transcripción
              </button>
              {transcript && (
                <button
                  type="button"
                  onClick={() => {
                    handleDeleteConv(transcript.id);
                  }}
                  className="py-2 px-4 bg-red-950/20 hover:bg-red-900/30 text-red-400 rounded-xl font-bold border border-red-500/10 hover:border-red-500/20 transition cursor-pointer flex items-center justify-center gap-1.5"
                  title="Eliminar conversación permanentemente"
                >
                  <Trash2 className="w-4 h-4" />
                  Eliminar Chat
                </button>
              )}
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
