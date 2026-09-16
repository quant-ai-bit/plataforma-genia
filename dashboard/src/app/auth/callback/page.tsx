"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase, isSupabaseConfigured } from "../../../lib/supabase";
import { Loader2, AlertCircle } from "lucide-react";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) {
      router.replace("/login");
      return;
    }

    // Check for errors in the URL
    if (typeof window !== "undefined") {
      const hash = window.location.hash;
      const search = window.location.search;
      const params = new URLSearchParams(search || hash.replace(/^#/, "?"));
      const errorDescription = params.get("error_description") || params.get("error");
      if (errorDescription) {
        setErrorMsg(decodeURIComponent(errorDescription));
        setTimeout(() => router.replace("/login"), 3500);
        return;
      }
    }

    // Listen for auth state change
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session) {
        router.replace("/analytics");
      }
    });

    // Check getSession immediately
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.replace("/analytics");
      }
    });

    // Safety timeout: redirect after 3.5s
    const timer = setTimeout(() => {
      router.replace("/analytics");
    }, 3500);

    return () => {
      subscription.unsubscribe();
      clearTimeout(timer);
    };
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center bg-[#070a12] text-white">
      <div className="flex flex-col items-center gap-3 p-8 bg-[#0b0f19] border border-white/[0.08] rounded-2xl shadow-2xl max-w-sm text-center">
        {errorMsg ? (
          <>
            <div className="p-3 bg-rose-500/10 text-rose-400 rounded-xl border border-rose-500/20">
              <AlertCircle className="w-8 h-8" />
            </div>
            <h3 className="font-bold text-base text-rose-300">Error de Autenticación</h3>
            <p className="text-xs text-slate-400">{errorMsg}</p>
            <p className="text-[11px] text-slate-500 mt-2">Redirigiendo al inicio de sesión...</p>
          </>
        ) : (
          <>
            <div className="p-3 bg-gradient-to-tr from-indigo-500 to-cyan-400 rounded-2xl shadow-lg shadow-indigo-500/25 animate-pulse">
              <Loader2 className="w-8 h-8 text-white animate-spin" />
            </div>
            <h3 className="font-bold text-base text-white">Iniciando Sesión</h3>
            <p className="text-xs text-slate-400">Verificando cuenta con Google y preparando la consola...</p>
          </>
        )}
      </div>
    </div>
  );
}
