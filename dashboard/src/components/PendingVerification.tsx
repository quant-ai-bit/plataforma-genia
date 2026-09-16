"use client";

import { useState } from "react";
import { useAppContext } from "../lib/AppContext";
import { 
  ShieldAlert, 
  Clock, 
  RefreshCw, 
  LogOut, 
  Sparkles, 
  Mail, 
  CheckCircle2 
} from "lucide-react";

export default function PendingVerification() {
  const { user, userProfile, logout, loadUserProfile } = useAppContext();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setFeedback(null);
    try {
      await loadUserProfile();
      setFeedback("Estado actualizado. Si tu cuenta ya fue autorizada, la consola se desbloqueará.");
    } catch (err) {
      setFeedback("No se pudo contactar al servidor. Intenta de nuevo en unos momentos.");
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#070b13] px-4 py-12 relative overflow-hidden">
      
      {/* Luces de fondo difuminadas */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-blue-900/10 blur-[140px] pointer-events-none"></div>
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-indigo-900/10 blur-[140px] pointer-events-none"></div>

      <div className="w-full max-w-lg space-y-8 bg-[#0d1321]/90 backdrop-blur-2xl p-8 sm:p-10 rounded-3xl border border-gray-800 shadow-2xl relative z-10 text-center animate-fadeIn">
        
        {/* Encabezado con logotipo de GENIA */}
        <div className="flex flex-col items-center">
          <div className="p-3 bg-gradient-to-tr from-blue-500 to-indigo-600 rounded-2xl shadow-lg shadow-blue-500/20 mb-4">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-black tracking-tight text-white">
            PLATAFORMA GENIA
          </h1>
          <p className="text-xs text-gray-400 mt-1 uppercase tracking-widest font-semibold">
            Portal de Clientes e Inteligencia Artificial
          </p>
        </div>

        {/* Indicador de Estado Pendiente */}
        <div className="space-y-4">
          <div className="mx-auto w-20 h-20 rounded-full bg-amber-500/10 border-2 border-amber-500/30 flex items-center justify-center text-amber-400 shadow-inner">
            <Clock className="w-10 h-10 animate-pulse" />
          </div>

          <div>
            <h2 className="text-xl font-bold text-white">
              Cuenta Pendiente de Verificación
            </h2>
            <p className="text-xs text-gray-400 mt-2">
              Hemos registrado con éxito tu cuenta asociada a:
            </p>
            <div className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 bg-gray-900 border border-gray-700 rounded-full text-xs font-semibold text-blue-400">
              <Mail className="w-3.5 h-3.5" />
              <span>{user?.email || userProfile?.email || "Cargando..."}</span>
            </div>
          </div>
        </div>

        {/* Tarjeta Explicativa */}
        <div className="bg-[#161f38]/60 border border-[#2d3a5f] rounded-2xl p-5 text-left text-xs text-gray-300 space-y-3">
          <div className="flex items-start gap-2.5">
            <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Acceso Restringido:</strong> Los nuevos usuarios no tienen acceso público inmediato a los agentes. 
              Un administrador de la plataforma debe <strong>autorizar tu cuenta</strong> y <strong>asignarte el agente de IA</strong> correspondiente a tu servicio.
            </p>
          </div>
          <div className="border-t border-gray-800/80 pt-3 flex items-center justify-between text-[11px] text-gray-400">
            <span>Estado actual:</span>
            <span className="px-2.5 py-0.5 bg-amber-500/20 text-amber-300 font-bold rounded-md border border-amber-500/30 uppercase tracking-wider text-[10px]">
              Pendiente de Asignación
            </span>
          </div>
        </div>

        {/* Notificación de feedback */}
        {feedback && (
          <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-300 text-xs flex items-center gap-2 text-left animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{feedback}</span>
          </div>
        )}

        {/* Botones de Acción */}
        <div className="space-y-3 pt-2">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-blue-500/10 hover:shadow-blue-500/20 transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
            <span>{isRefreshing ? "Consultando estado..." : "Verificar Estado de Autorización"}</span>
          </button>

          <button
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-transparent hover:bg-gray-800/50 text-gray-400 hover:text-white text-xs font-semibold rounded-xl border border-gray-800 transition cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5 text-gray-400" />
            <span>Cerrar Sesión</span>
          </button>
        </div>

        {/* Pie de soporte */}
        <div className="pt-4 border-t border-gray-850 text-[11px] text-gray-500">
          ¿Tienes dudas o necesitas activación prioritaria? Contáctanos a{" "}
          <a 
            href="mailto:conecta@genia.com.co" 
            className="text-blue-400 hover:underline font-medium"
          >
            conecta@genia.com.co
          </a>
        </div>

      </div>
    </div>
  );
}
