"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppContext } from "../lib/AppContext";
import {
  LayoutDashboard,
  Bot,
  UserCheck,
  MessageSquare,
  Sparkles,
  LogOut,
  FolderOpen,
  Settings,
  X,
  ShieldCheck
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout, isSupabaseConfigured, isBackendOnline, agents } = useAppContext();

  // Check if we are in an agent-specific route
  const agentRouteMatch = pathname.match(/^\/agents\/([^\/]+)/);
  const activeAgentId = agentRouteMatch ? agentRouteMatch[1] : null;
  const activeAgent = activeAgentId ? agents.find(a => a.id === activeAgentId) : null;

  const isActive = (path: string) => {
    if (path === "/analytics") {
      return pathname === "/analytics";
    }
    return pathname.startsWith(path);
  };

  const navItemClass = (active: boolean) =>
    `w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition ${
      active
        ? "bg-gradient-to-r from-blue-600/25 to-indigo-600/10 text-blue-400 border border-blue-500/25"
        : "text-gray-400 hover:bg-gray-800/40 hover:text-gray-200 border border-transparent"
    }`;

  const subNavItemClass = (active: boolean) =>
    `w-full flex items-center gap-2.5 pl-9 pr-4 py-2 rounded-lg text-xs font-semibold transition ${
      active
        ? "text-blue-400 bg-blue-500/5 border-l-2 border-blue-500"
        : "text-gray-500 hover:text-gray-300 border-l-2 border-transparent"
    }`;

  return (
    <aside className="w-64 bg-[#0d1321] border-r border-[#1e293b] flex flex-col justify-between h-screen flex-shrink-0">
      <div className="overflow-y-auto flex-1">
        {/* Logo y título de marca */}
        <div className="h-20 flex items-center px-6 gap-3 border-b border-[#1e293b] bg-[#0c101c]">
          <div className="p-2 bg-gradient-to-tr from-blue-500 to-purple-600 rounded-lg shadow-lg">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-500 bg-clip-text text-transparent">
              GENIA
            </h1>
            <span className="text-[10px] text-gray-500 tracking-widest font-semibold block uppercase">
              Platform MVP
            </span>
          </div>
        </div>

        {/* Demo Mode banner */}
        {!isSupabaseConfigured && (
          <div className="mx-4 mt-4 p-3 rounded-xl bg-amber-500/5 border border-amber-500/15 text-[11px] text-amber-400">
            <span className="font-semibold block mb-0.5">⚠️ Modo Demo Local</span>
            Supabase Auth no está configurado. La seguridad de la API está omitida.
          </div>
        )}

        {/* Enlaces de menú */}
        <nav className="p-4 space-y-1.5">
          <Link href="/analytics" className={navItemClass(isActive("/analytics"))}>
            <LayoutDashboard className="w-4 h-4" />
            Consola Analítica
          </Link>
          
          <Link href="/agents" className={navItemClass(isActive("/agents") && !activeAgentId)}>
            <Bot className="w-4 h-4" />
            Creador de Agentes
          </Link>

          {/* Sub-navigation for active agent */}
          {activeAgentId && (
            <div className="space-y-1 my-2 bg-gray-950/25 p-2 rounded-xl border border-gray-900/60 animate-fadeIn">
              <div className="px-3 py-1.5 text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center justify-between">
                <span>Agente: {activeAgent?.name || "Cargando..."}</span>
                <Link href="/agents" className="text-gray-500 hover:text-white transition" title="Cerrar vista de agente">
                  <X className="w-3 h-3" />
                </Link>
              </div>

              <Link href={`/agents/${activeAgentId}`} className={subNavItemClass(pathname === `/agents/${activeAgentId}`)}>
                <Settings className="w-3.5 h-3.5" />
                Configuración
              </Link>
              
              <Link href={`/agents/${activeAgentId}/knowledge`} className={subNavItemClass(pathname === `/agents/${activeAgentId}/knowledge`)}>
                <FolderOpen className="w-3.5 h-3.5" />
                Conocimiento RAG
              </Link>
              
              <Link href={`/agents/${activeAgentId}/chat`} className={subNavItemClass(pathname === `/agents/${activeAgentId}/chat`)}>
                <Sparkles className="w-3.5 h-3.5" />
                Simulador Sandbox
              </Link>
            </div>
          )}

          <Link href="/leads" className={navItemClass(isActive("/leads"))}>
            <UserCheck className="w-4 h-4" />
            Leads Capturados
          </Link>

          <Link href="/conversations" className={navItemClass(isActive("/conversations"))}>
            <MessageSquare className="w-4 h-4" />
            Historial de Chats
          </Link>

          <Link href="/evidence" className={navItemClass(isActive("/evidence"))}>
            <ShieldCheck className="w-4 h-4" />
            Evidencias y Auditoría
          </Link>

          {isSupabaseConfigured && user && (
            <button
              onClick={logout}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition text-red-400 hover:bg-red-500/10 border border-transparent cursor-pointer mt-4"
            >
              <LogOut className="w-4 h-4 text-red-500" />
              <span className="text-red-400 hover:text-red-300">Cerrar Sesión</span>
            </button>
          )}
        </nav>
      </div>

      {/* Footer del sidebar con estado de conexión */}
      <div className="p-4 border-t border-[#1e293b] bg-[#0c101c]/50">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${isBackendOnline ? "bg-green-500 shadow-green-500/50" : "bg-amber-500 shadow-amber-500/50"} animate-pulse shadow-sm`}></span>
          <div className="text-xs">
            <p className="font-semibold text-gray-300">
              Servidor Backend
            </p>
            <p className="text-[10px] text-gray-500">
              {isBackendOnline ? "Online (Puerto 8000)" : "Offline (Modo Demo)"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
