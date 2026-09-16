"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useAppContext } from "../../lib/AppContext";
import Sidebar from "../../components/Sidebar";
import PendingVerification from "../../components/PendingVerification";
import { checkIsAdmin } from "../../lib/types";
import { Loader2, RefreshCw, AlertTriangle, Bell, Shield } from "lucide-react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { 
    user, 
    userProfile, 
    pendingUsersCount, 
    authLoading, 
    isSupabaseConfigured, 
    isBackendOnline, 
    checkHealthAndLoadData 
  } = useAppContext();

  useEffect(() => {
    if (!authLoading) {
      const hasAuthParams = typeof window !== "undefined" && (
        window.location.hash.includes("access_token") || 
        window.location.hash.includes("refresh_token") ||
        window.location.search.includes("code=")
      );
      if (isSupabaseConfigured && !user && !hasAuthParams) {
        router.push("/login");
      }
    }
  }, [authLoading, user, isSupabaseConfigured, router]);

  // Page title mapping based on route path
  const getHeaderTitle = () => {
    if (pathname === "/analytics") return "Resumen Ejecutivo";
    if (pathname === "/conversations") return "Conversaciones (Inbox)";
    if (pathname === "/leads") return "CRM Pipeline";
    if (pathname === "/agenda") return "Agenda & Citas";
    if (pathname === "/catalog") return "Catálogo de Productos & Propiedades";
    if (pathname === "/workflows") return "Flujos & Automatizaciones";
    if (pathname === "/integrations") return "Hub de Integraciones Nativas";
    if (pathname === "/settings") return "Mi Negocio";
    if (pathname === "/admin") return "Super Admin Master Console";
    if (pathname === "/agents") return "Ingeniería de Agentes";
    if (pathname === "/users") return "Gestión de Usuarios y Accesos";
    if (pathname.includes("/knowledge")) return "Base de Conocimiento RAG";
    if (pathname.includes("/chat")) return "Simulador Sandbox E2E";
    if (pathname.startsWith("/agents/")) return "Configuración Técnica de Agente";
    if (pathname === "/evidence") return "Evidencias y Auditoría";
    return "Consola GENIA";
  };

  const getHeaderSub = () => {
    if (pathname === "/analytics") return "Métricas operativas, interacciones y estado en tiempo real.";
    if (pathname === "/conversations") return "Bandeja omnicanal en vivo: WhatsApp, Telegram y Chat Web.";
    if (pathname === "/leads") return "Embudo de oportunidades con etapas y gestión visual de prospectos.";
    if (pathname === "/agenda") return "Sincronización de citas y reuniones con Google Calendar y Outlook.";
    if (pathname === "/catalog") return "Inventario comercial para respuestas de IA y consulta interactiva.";
    if (pathname === "/workflows") return "Automatizaciones nativas por eventos, condiciones y acciones.";
    if (pathname === "/integrations") return "Conectores directos sin intermediarios para WhatsApp, Telegram y más.";
    if (pathname === "/settings") return "Perfil corporativo, datos de contacto, horarios y preferencias.";
    if (pathname === "/admin") return "Control maestro de subcuentas, tiers, rotación de modelos LLM y auditoría.";
    if (pathname === "/agents") return "Configuración y comportamiento técnico de agentes de IA.";
    if (pathname === "/users") return "Aprobación de cuentas y asignación de agentes de IA.";
    if (pathname.includes("/knowledge")) return "Documentos vectorizados y RAG para entrenamiento de agentes.";
    if (pathname.includes("/chat")) return "Pruebas interactivas y diagnóstico en vivo del agente.";
    if (pathname.startsWith("/agents/")) return "Parámetros avanzados, prompts del sistema y herramientas.";
    if (pathname === "/evidence") return "Registro forense de actividad y pruebas de integridad.";
    return "Plataforma autónoma de agentes de Inteligencia Artificial & CRM.";
  };

  const hasAuthParams = typeof window !== "undefined" && (
    window.location.hash.includes("access_token") || 
    window.location.hash.includes("refresh_token") ||
    window.location.search.includes("code=")
  );

  if (authLoading || (hasAuthParams && !user)) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#070a12] text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="p-3 bg-gradient-to-tr from-indigo-500 to-cyan-400 rounded-2xl shadow-lg shadow-indigo-500/25 animate-pulse">
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          </div>
          <p className="text-slate-400 text-sm font-medium">
            {hasAuthParams ? "Autenticando sesión con Google..." : "Verificando credenciales..."}
          </p>
        </div>
      </div>
    );
  }

  if (isSupabaseConfigured && !user && !hasAuthParams) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#070a12] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-slate-400 text-sm">Redireccionando al inicio de sesión...</p>
        </div>
      </div>
    );
  }

  // Si la cuenta está pendiente de verificación y no es administrador, mostrar pantalla de espera
  if (userProfile && userProfile.status === "pending" && userProfile.role !== "admin") {
    return <PendingVerification />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#070a12]">
      {/* Dynamic Sidebar */}
      <Sidebar />

      {/* Main Content Pane */}
      <main className="flex-1 flex flex-col overflow-hidden bg-[#070a12]">
        {/* Header Superior - genia.com.co design */}
        <header className="h-20 border-b border-white/[0.08] bg-[#0b0f19]/80 backdrop-blur-xl flex items-center justify-between px-8 flex-shrink-0 z-10">
          <div>
            <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-2.5">
              {getHeaderTitle()}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {getHeaderSub()}
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            {isBackendOnline === false && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-950/40 border border-amber-500/20 text-amber-300 text-xs rounded-xl">
                <AlertTriangle className="w-3.5 h-3.5 animate-pulse" />
                <span>Servidor local</span>
              </div>
            )}

            {/* Notificaciones (Solo Administradores) */}
            {userProfile?.role === "admin" && (
              <Link
                href="/users"
                className="relative p-2.5 text-slate-400 hover:text-white bg-[#0b0f19] hover:bg-slate-800/60 border border-white/[0.08] rounded-xl transition shadow-sm"
                title={pendingUsersCount > 0 ? `${pendingUsersCount} usuario(s) pendiente(s) de autorización` : "Gestión de Usuarios"}
              >
                <Bell className="w-4 h-4" />
                {pendingUsersCount > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-gradient-to-r from-red-500 to-rose-600 text-white font-black text-[9px] rounded-full flex items-center justify-center border-2 border-[#070a12] animate-pulse shadow-lg shadow-rose-500/50">
                    {pendingUsersCount}
                  </span>
                )}
              </Link>
            )}
            
            <button 
              onClick={checkHealthAndLoadData}
              className="p-2.5 text-slate-400 hover:text-white bg-[#0b0f19] hover:bg-slate-800/60 border border-white/[0.08] rounded-xl transition shadow-sm cursor-pointer"
              title="Sincronizar Datos"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {user && (
              <div className="flex items-center gap-2.5 pl-3 border-l border-white/[0.08]">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-cyan-400 p-[1px] shadow-sm">
                  <div className="w-full h-full rounded-full bg-[#0b0f19] flex items-center justify-center text-xs font-bold text-indigo-300">
                    {user.email?.[0].toUpperCase() || "U"}
                  </div>
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-slate-200 font-medium hidden md:inline truncate max-w-[140px]" title={user.email}>
                    {user.email?.split("@")[0]}
                  </span>
                  {checkIsAdmin(user?.email, userProfile?.role) ? (
                    <span className="text-[9px] font-bold uppercase tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400 hidden md:inline">
                      Super Admin
                    </span>
                  ) : userProfile?.assigned_agent ? (
                    <span className="text-[9px] text-slate-400 font-medium truncate max-w-[140px] hidden md:inline">
                      {userProfile.assigned_agent.name}
                    </span>
                  ) : (
                    <span className="text-[9px] text-slate-400 hidden md:inline">
                      Cliente
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Tab/Page Content scroll region */}
        <div className="flex-1 overflow-y-auto p-8 bg-[#070a12]">
          {children}
        </div>
      </main>
    </div>
  );
}
