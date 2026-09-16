"use client";

import { useState, useEffect } from "react";
import { useAppContext } from "../../../lib/AppContext";
import { authenticatedFetch } from "../../../lib/api";
import { UserProfile, Agent } from "../../../lib/types";
import {
  Users,
  UserCheck,
  UserX,
  Clock,
  ShieldCheck,
  Bot,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Mail,
  Calendar,
  ArrowRight
} from "lucide-react";

export default function UsersManagementPage() {
  const { userProfile, agents, loadPendingUsersCount } = useAppContext();
  const [activeTab, setActiveTab] = useState<"pending" | "active">("pending");
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Mapa de selección de agentes por usuario pendiente: { [userId]: agentId }
  const [selectedAgents, setSelectedAgents] = useState<Record<string, string>>({});

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authenticatedFetch(`/api/users`);
      if (res.ok) {
        const data: UserProfile[] = await res.json();
        setUsers(data);
        // Pre-seleccionar el primer agente disponible para cada usuario pendiente que no tenga selección
        const initialSelections: Record<string, string> = {};
        const defaultAgentId = agents.length > 0 ? agents[0].id : "";
        data.forEach(u => {
          if (u.status === "pending") {
            initialSelections[u.id] = defaultAgentId;
          }
        });
        setSelectedAgents(initialSelections);
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.detail || "Error al cargar la lista de usuarios.");
      }
    } catch (err: any) {
      setError(err.message || "Error al conectar con el servidor.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleAuthorize = async (userId: string) => {
    const agentId = selectedAgents[userId] || (agents.length > 0 ? agents[0].id : null);
    if (!agentId) {
      setError("Debes seleccionar un agente de IA para asignárselo al usuario.");
      return;
    }

    setActionLoading(userId);
    setError(null);
    setSuccess(null);

    try {
      const res = await authenticatedFetch(`/api/users/${userId}/authorize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assigned_agent_id: agentId }),
      });

      if (res.ok) {
        const updated: UserProfile = await res.json();
        setSuccess(`Usuario ${updated.email} autorizado exitosamente con el agente seleccionado.`);
        await loadUsers();
        await loadPendingUsersCount();
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.detail || "No se pudo autorizar al usuario.");
      }
    } catch (err: any) {
      setError(err.message || "Error al realizar la autorización.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (userId: string) => {
    if (!confirm("¿Estás seguro de que deseas rechazar o suspender el acceso de este usuario?")) {
      return;
    }

    setActionLoading(userId);
    setError(null);
    setSuccess(null);

    try {
      const res = await authenticatedFetch(`/api/users/${userId}/reject`, {
        method: "POST",
      });

      if (res.ok) {
        setSuccess("El usuario ha sido rechazado.");
        await loadUsers();
        await loadPendingUsersCount();
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.detail || "No se pudo rechazar la solicitud.");
      }
    } catch (err: any) {
      setError(err.message || "Error al rechazar usuario.");
    } finally {
      setActionLoading(null);
    }
  };

  // Filtrar según pestaña
  const pendingUsers = users.filter(u => u.status === "pending");
  const activeUsers = users.filter(u => u.status === "active");

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      
      {/* Encabezado superior */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[#0d1321]/60 p-6 rounded-3xl border border-gray-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/20">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-black text-white">Gestión y Acreditación de Usuarios</h1>
              <p className="text-xs text-gray-400 mt-0.5">
                Controla quién accede a la plataforma y qué agente de IA atiende a cada cliente.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={loadUsers}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-900 hover:bg-gray-800 text-gray-300 hover:text-white text-xs font-semibold rounded-xl border border-gray-700 transition cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Actualizar Lista</span>
        </button>
      </div>

      {/* Mensajes de Feedback */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-3 animate-fadeIn">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="p-4 rounded-2xl bg-green-500/10 border border-green-500/20 text-green-400 text-xs flex items-center gap-3 animate-fadeIn">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Selector de Pestañas */}
      <div className="flex border-b border-gray-800 gap-6">
        <button
          onClick={() => setActiveTab("pending")}
          className={`pb-3.5 text-xs font-bold transition relative flex items-center gap-2 cursor-pointer ${
            activeTab === "pending"
              ? "text-blue-400 border-b-2 border-blue-500"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Pendientes de Aprobación</span>
          {pendingUsers.length > 0 && (
            <span className="px-2 py-0.5 bg-red-600 text-white rounded-full text-[10px] font-black animate-pulse">
              {pendingUsers.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("active")}
          className={`pb-3.5 text-xs font-bold transition relative flex items-center gap-2 cursor-pointer ${
            activeTab === "active"
              ? "text-blue-400 border-b-2 border-blue-500"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Usuarios Activos y Autorizados</span>
          <span className="px-2 py-0.5 bg-gray-800 text-gray-300 rounded-full text-[10px] font-bold">
            {activeUsers.length}
          </span>
        </button>
      </div>

      {/* Contenido según Pestaña */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-gray-500">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-xs">Cargando usuarios registrados...</p>
        </div>
      ) : activeTab === "pending" ? (
        /* --- LISTA DE PENDIENTES --- */
        <div className="space-y-4">
          {pendingUsers.length === 0 ? (
            <div className="bg-[#0d1321]/40 border border-gray-850 rounded-3xl p-12 text-center space-y-3">
              <div className="mx-auto w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-white">No hay solicitudes pendientes</h3>
              <p className="text-xs text-gray-400 max-w-md mx-auto">
                Todos los usuarios registrados han sido evaluados o cuentan con un agente asignado.
              </p>
            </div>
          ) : (
            pendingUsers.map((u) => (
              <div
                key={u.id}
                className="bg-[#0d1321]/80 border border-gray-800 hover:border-blue-500/30 rounded-2xl p-6 transition flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6"
              >
                {/* Datos del usuario */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 bg-amber-500/15 text-amber-400 border border-amber-500/30 rounded-md text-[10px] font-extrabold uppercase tracking-wider">
                      Pendiente
                    </span>
                    <span className="text-[11px] text-gray-500 flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {u.created_at ? new Date(u.created_at).toLocaleString() : "Reciente"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-blue-400 flex-shrink-0" />
                    <span className="text-sm font-bold text-white">{u.email}</span>
                  </div>

                  <p className="text-[11px] text-gray-400">
                    ID de Usuario: <span className="font-mono text-gray-500">{u.id}</span>
                  </p>
                </div>

                {/* Controles de Asignación y Aprobación */}
                <div className="w-full lg:w-auto flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  {/* Selector de Agente */}
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                      Agente a Integrar:
                    </label>
                    <div className="relative">
                      <select
                        value={selectedAgents[u.id] || (agents[0]?.id || "")}
                        onChange={(e) =>
                          setSelectedAgents(prev => ({ ...prev, [u.id]: e.target.value }))
                        }
                        className="bg-[#161f38] border border-[#2d3a5f] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 min-w-[220px]"
                      >
                        {agents.map((ag) => (
                          <option key={ag.id} value={ag.id}>
                            {ag.name} ({ag.model})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Botón Autorizar */}
                  <div className="flex items-end gap-2 pt-4 sm:pt-0">
                    <button
                      onClick={() => handleAuthorize(u.id)}
                      disabled={actionLoading === u.id || agents.length === 0}
                      className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-md shadow-blue-500/10 transition cursor-pointer disabled:opacity-50"
                    >
                      {actionLoading === u.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Autorizar y Conectar</span>
                        </>
                      )}
                    </button>

                    {/* Botón Rechazar */}
                    <button
                      onClick={() => handleReject(u.id)}
                      disabled={actionLoading === u.id}
                      className="p-2 bg-gray-900 hover:bg-red-500/10 text-gray-400 hover:text-red-400 border border-gray-800 hover:border-red-500/20 rounded-xl transition cursor-pointer"
                      title="Rechazar solicitud"
                    >
                      <UserX className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        /* --- LISTA DE ACTIVOS --- */
        <div className="space-y-4">
          {activeUsers.length === 0 ? (
            <div className="bg-[#0d1321]/40 border border-gray-850 rounded-3xl p-12 text-center text-gray-400 text-xs">
              No hay usuarios activos registrados aún.
            </div>
          ) : (
            <div className="overflow-x-auto bg-[#0d1321]/70 border border-gray-800 rounded-2xl">
              <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-[#161f38]/50 border-b border-gray-800 text-[10px] uppercase font-bold text-gray-400">
                  <tr>
                    <th className="px-6 py-4">Usuario</th>
                    <th className="px-6 py-4">Rol</th>
                    <th className="px-6 py-4">Agente Asignado</th>
                    <th className="px-6 py-4">Autorizado Por</th>
                    <th className="px-6 py-4">Fecha Aprobación</th>
                    <th className="px-6 py-4 text-right">Reasignar Agente</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-850">
                  {activeUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-800/20 transition">
                      <td className="px-6 py-4 font-semibold text-white">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center text-xs font-bold">
                            {u.email[0].toUpperCase()}
                          </div>
                          <span>{u.email}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          u.role === "admin" 
                            ? "bg-purple-500/20 text-purple-300 border border-purple-500/30" 
                            : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {u.assigned_agent ? (
                          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                            <Bot className="w-3.5 h-3.5" />
                            <span>{u.assigned_agent.name}</span>
                          </div>
                        ) : (
                          <span className="text-gray-500 italic">
                            {u.role === "admin" ? "Todos los agentes (Admin)" : "Sin agente"}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-gray-400">
                        {u.approved_by || (u.role === "admin" ? "Sistema (Root)" : "—")}
                      </td>
                      <td className="px-6 py-4 text-gray-400">
                        {u.approved_at ? new Date(u.approved_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {u.role !== "admin" ? (
                          <div className="flex items-center justify-end gap-2">
                            <select
                              value={selectedAgents[u.id] || u.assigned_agent_id || ""}
                              onChange={(e) =>
                                setSelectedAgents(prev => ({ ...prev, [u.id]: e.target.value }))
                              }
                              className="bg-[#161f38] border border-[#2d3a5f] rounded-lg px-2 py-1 text-[11px] text-white focus:outline-none"
                            >
                              {agents.map((ag) => (
                                <option key={ag.id} value={ag.id}>
                                  {ag.name}
                                </option>
                              ))}
                            </select>
                            <button
                              onClick={() => handleAuthorize(u.id)}
                              disabled={actionLoading === u.id}
                              className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-bold rounded-lg transition"
                            >
                              Guardar
                            </button>
                          </div>
                        ) : (
                          <span className="text-gray-600 text-[11px]">Acceso total</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
