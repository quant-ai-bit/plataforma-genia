"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAppContext } from "../../lib/AppContext";
import Sidebar from "../../components/Sidebar";
import { Loader2, RefreshCw, AlertTriangle } from "lucide-react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, authLoading, isSupabaseConfigured, isBackendOnline, checkHealthAndLoadData } = useAppContext();

  useEffect(() => {
    if (!authLoading) {
      if (isSupabaseConfigured && !user) {
        router.push("/login");
      }
    }
  }, [authLoading, user, isSupabaseConfigured, router]);

  // Page title mapping based on route path
  const getHeaderTitle = () => {
    if (pathname === "/analytics") return "Consola Analítica";
    if (pathname === "/agents") return "Creador e Ingeniería de Agentes";
    if (pathname.includes("/knowledge")) return "Base de Conocimiento RAG";
    if (pathname.includes("/chat")) return "Simulador Sandbox E2E";
    if (pathname.startsWith("/agents/")) return "Configuración de Agente";
    if (pathname === "/leads") return "Leads Capturados";
    if (pathname === "/conversations") return "Historial de Chats";
    return "Consola GENIA";
  };

  const getHeaderSub = () => {
    if (pathname === "/analytics") return "Estadísticas y métricas generales del ecosistema.";
    if (pathname === "/agents") return "Crea, modifica y despliega agentes de Inteligencia Artificial.";
    if (pathname.includes("/knowledge")) return "Gestiona los documentos del almacenamiento de RAG.";
    if (pathname.includes("/chat")) return "Interactúa y pon a prueba tu agente en tiempo real.";
    if (pathname.startsWith("/agents/")) return "Modifica el comportamiento, modelo y parámetros del agente.";
    if (pathname === "/leads") return "Monitorea la captura automática de clientes potenciales.";
    if (pathname === "/conversations") return "Historial completo de conversaciones activas e inactivas.";
    return "Consola administrativa para gestionar el ecosistema GENIA IA.";
  };

  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#070b13] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-sm">Verificando sesión...</p>
        </div>
      </div>
    );
  }

  if (isSupabaseConfigured && !user) {
    // Show a loading/redirecting spinner while useEffect pushes to /login
    return (
      <div className="flex h-screen items-center justify-center bg-[#070b13] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-sm">Redireccionando al login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#070b13]">
      {/* Dynamic Sidebar */}
      <Sidebar />

      {/* Main Content Pane */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header Superior */}
        <header className="h-20 border-b border-[#1e293b] bg-[#0c101c]/45 flex items-center justify-between px-8 flex-shrink-0">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white capitalize">
              {getHeaderTitle()}
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {getHeaderSub()}
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            {isBackendOnline === false && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-950/40 border border-amber-500/20 text-amber-300 text-xs rounded-xl">
                <AlertTriangle className="w-3.5 h-3.5 animate-pulse" />
                <span>Usando servidor mock local</span>
              </div>
            )}
            
            <button 
              onClick={checkHealthAndLoadData}
              className="p-2 text-gray-400 hover:text-white bg-gray-800/40 hover:bg-gray-800 border border-gray-700 rounded-xl transition"
              title="Sincronizar Datos"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {user && (
              <div className="flex items-center gap-2 pl-2 border-l border-gray-800">
                <div className="w-8 h-8 rounded-full bg-blue-600/35 border border-blue-500/30 flex items-center justify-center text-xs font-bold text-blue-200">
                  {user.email?.[0].toUpperCase() || "U"}
                </div>
                <span className="text-xs text-gray-300 font-medium hidden md:inline truncate max-w-[120px]" title={user.email}>
                  {user.email?.split("@")[0]}
                </span>
              </div>
            )}
          </div>
        </header>

        {/* Tab/Page Content scroll region */}
        <div className="flex-1 overflow-y-auto p-8 bg-[#080d1a]">
          {children}
        </div>
      </main>
    </div>
  );
}
