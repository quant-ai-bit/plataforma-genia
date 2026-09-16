"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppContext } from "../lib/AppContext";
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  Calendar,
  Package,
  GitBranch,
  Puzzle,
  Building2,
  ShieldAlert,
  Bot,
  UserCheck,
  ShieldCheck,
  LogOut,
  FolderOpen,
  Settings,
  Sparkles,
  X
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { 
    user, 
    userProfile, 
    pendingUsersCount, 
    logout, 
    isSupabaseConfigured, 
    isBackendOnline, 
    agents 
  } = useAppContext();

  // Strict role security: NEVER assume admin if profile is null or undefined!
  const isAdmin = userProfile?.role === "admin";

  // Check if we are in an agent-specific route (for admin sub-navigation)
  const agentRouteMatch = pathname.match(/^\/agents\/([^\/]+)/);
  const activeAgentId = agentRouteMatch ? agentRouteMatch[1] : null;
  const activeAgent = activeAgentId ? agents.find(a => a.id === activeAgentId) : null;

  const isActive = (path: string) => {
    if (path === "/analytics") {
      return pathname === "/analytics";
    }
    return pathname === path || pathname.startsWith(path + "/");
  };

  const navItemClass = (active: boolean) =>
    `w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
      active
        ? "bg-gradient-to-r from-indigo-600/20 via-indigo-500/10 to-transparent text-cyan-300 border border-indigo-500/30 shadow-[0_0_15px_-3px_rgba(79,70,229,0.25)]"
        : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-100 border border-transparent"
    }`;

  const subNavItemClass = (active: boolean) =>
    `w-full flex items-center gap-2 pl-7 pr-3 py-1.5 rounded-lg text-xs font-semibold transition ${
      active
        ? "text-cyan-300 bg-cyan-500/10 border-l-2 border-cyan-400"
        : "text-slate-400 hover:text-slate-200 border-l-2 border-transparent"
    }`;

  // 8 Mandatory Client Modules for `user` role
  const clientNavItems = [
    { name: "Resumen", path: "/analytics", icon: LayoutDashboard },
    { name: "Conversaciones", path: "/conversations", icon: MessageSquare },
    { name: "CRM", path: "/leads", icon: Users },
    { name: "Agenda", path: "/agenda", icon: Calendar },
    { name: "Catálogo", path: "/catalog", icon: Package },
    { name: "Flujos", path: "/workflows", icon: GitBranch },
    { name: "Integraciones", path: "/integrations", icon: Puzzle },
    { name: "Mi Negocio", path: "/settings", icon: Building2 },
  ];

  return (
    <aside className="w-64 bg-[#0b0f19] border-r border-white/[0.08] flex flex-col justify-between h-screen flex-shrink-0 select-none z-20">
      <div className="overflow-y-auto flex-1 flex flex-col">
        {/* Brand Header */}
        <div className="h-20 flex items-center px-6 gap-3 border-b border-white/[0.08] bg-[#0b0f19]">
          <div className="p-2.5 bg-gradient-to-tr from-[#4f46e5] via-[#6366f1] to-[#38bdf8] rounded-xl shadow-lg shadow-indigo-500/25">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-[#4f46e5] via-[#6366f1] to-[#38bdf8] bg-clip-text text-transparent">
              GENIA
            </h1>
            <span className="text-[10px] text-slate-400 tracking-widest font-semibold block uppercase">
              AI & CRM Platform
            </span>
          </div>
        </div>

        {/* Local Demo Warning Banner */}
        {!isSupabaseConfigured && (
          <div className="mx-4 mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300">
            <span className="font-semibold block mb-0.5">⚠️ Modo Demo Local</span>
            Autenticación Supabase no detectada.
          </div>
        )}

        {/* Navigation list */}
        <nav className="p-4 space-y-1">
          {/* If Super Admin, show Master Admin controls at the top */}
          {isAdmin && (
            <div className="mb-4">
              <div className="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldAlert className="w-3 h-3 text-indigo-400" />
                <span>Super Admin</span>
              </div>
              <div className="space-y-1 mt-1.5">
                <Link href="/admin" className={navItemClass(isActive("/admin"))}>
                  <ShieldAlert className="w-4 h-4 text-indigo-400" />
                  <span className="flex-1">Panel Master</span>
                  <span className="px-1.5 py-0.5 text-[9px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-md">
                    Admin
                  </span>
                </Link>

                <Link href="/agents" className={navItemClass(isActive("/agents") && !activeAgentId)}>
                  <Bot className="w-4 h-4 text-indigo-400" />
                  <span>Agentes & LLM</span>
                </Link>

                {/* Sub-navegación si un agente está seleccionado en ruta /agents/[id] */}
                {activeAgentId && (
                  <div className="space-y-1 my-2 bg-[#070a12]/80 p-2 rounded-xl border border-white/[0.08] animate-fadeIn">
                    <div className="px-2 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                      <span className="truncate max-w-[130px]">{activeAgent?.name || "Agente"}</span>
                      <Link href="/agents" className="text-slate-400 hover:text-white transition" title="Cerrar">
                        <X className="w-3 h-3" />
                      </Link>
                    </div>

                    <Link href={`/agents/${activeAgentId}`} className={subNavItemClass(pathname === `/agents/${activeAgentId}`)}>
                      <Settings className="w-3 h-3" />
                      Configuración
                    </Link>
                    
                    <Link href={`/agents/${activeAgentId}/knowledge`} className={subNavItemClass(pathname === `/agents/${activeAgentId}/knowledge`)}>
                      <FolderOpen className="w-3 h-3" />
                      Conocimiento RAG
                    </Link>
                    
                    <Link href={`/agents/${activeAgentId}/chat`} className={subNavItemClass(pathname === `/agents/${activeAgentId}/chat`)}>
                      <Sparkles className="w-3 h-3" />
                      Simulador Sandbox
                    </Link>
                  </div>
                )}

                <Link href="/users" className={navItemClass(isActive("/users"))}>
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-3">
                      <UserCheck className="w-4 h-4 text-indigo-400" />
                      <span>Usuarios</span>
                    </div>
                    {pendingUsersCount > 0 && (
                      <span className="px-1.5 py-0.2 text-[9px] font-black bg-rose-600 text-white rounded-full animate-pulse shadow-sm">
                        {pendingUsersCount}
                      </span>
                    )}
                  </div>
                </Link>

                <Link href="/evidence" className={navItemClass(isActive("/evidence"))}>
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  <span>Auditoría</span>
                </Link>
              </div>

              <div className="my-3 border-t border-white/[0.08]"></div>
              <div className="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Módulos Operativos
              </div>
            </div>
          )}

          {/* 8 Standard Client Modules (Shown for normal users and operational admins) */}
          {clientNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link key={item.path} href={item.path} className={navItemClass(active)}>
                <Icon className={`w-4 h-4 ${active ? "text-cyan-300" : "text-slate-400"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}

          {/* Logout Action */}
          {isSupabaseConfigured && user && (
            <button
              onClick={logout}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition text-rose-400 hover:bg-rose-500/10 border border-transparent cursor-pointer mt-4"
            >
              <LogOut className="w-4 h-4 text-rose-400" />
              <span>Cerrar Sesión</span>
            </button>
          )}
        </nav>
      </div>

      {/* Sidebar Footer with system telemetry */}
      <div className="p-4 border-t border-white/[0.08] bg-[#0b0f19]">
        <div className="flex items-center gap-2.5">
          <span className={`w-2 h-2 rounded-full ${isBackendOnline ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" : "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]"} animate-pulse`}></span>
          <div className="text-xs">
            <p className="font-semibold text-slate-300 leading-tight">
              GENIA Cloud Engine
            </p>
            <p className="text-[10px] text-slate-400">
              {isBackendOnline 
                ? (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") 
                  ? "Conectado (Local 8000)" 
                  : "Conectado (Producción)") 
                : "Modo Offline"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
