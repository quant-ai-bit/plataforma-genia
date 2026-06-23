"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "../../../lib/AppContext";
import { supabase } from "../../../lib/supabase";
import { Sparkles, Loader2, AlertTriangle } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { user, authLoading, isSupabaseConfigured } = useAppContext();

  const [isRegistering, setIsRegistering] = useState<boolean>(false);
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [submitLoading, setSubmitLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!authLoading) {
      if (!isSupabaseConfigured || user) {
        router.push("/analytics");
      }
    }
  }, [authLoading, user, isSupabaseConfigured, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitLoading(true);

    if (!isSupabaseConfigured || !supabase) {
      setError("Supabase no está configurado.");
      setSubmitLoading(false);
      return;
    }

    try {
      if (isRegistering) {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
        });
        if (signUpError) throw signUpError;
        alert("¡Registro exitoso! Por favor verifica tu correo electrónico para confirmar la cuenta.");
        setIsRegistering(false);
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInError) throw signInError;
        router.push("/analytics");
      }
    } catch (err: any) {
      setError(err.message || "Ocurrió un error en el proceso.");
    } finally {
      setSubmitLoading(false);
    }
  };

  if (authLoading || (!user && !isSupabaseConfigured)) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#070b13] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-sm">Verificando sesión...</p>
        </div>
      </div>
    );
  }

  // If user is already logged in, show loading as we redirect
  if (user) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#070b13] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-sm">Redireccionando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#070b13] px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 bg-[#0d1321] p-8 rounded-2xl border border-[#1e293b] shadow-2xl">
        <div className="flex flex-col items-center">
          <div className="p-3 bg-gradient-to-tr from-blue-500 to-purple-600 rounded-2xl shadow-lg mb-4">
            <Sparkles className="w-8 h-8 text-white animate-pulse" />
          </div>
          <h2 className="text-center text-3xl font-extrabold text-white">
            {isRegistering ? "Crear cuenta en GENIA" : "Iniciar sesión"}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-400">
            {isRegistering ? "¿Ya tienes una cuenta?" : "¿Nuevo en la plataforma?"}{" "}
            <button
              type="button"
              onClick={() => {
                setIsRegistering(!isRegistering);
                setError(null);
              }}
              className="font-medium text-blue-400 hover:text-blue-300 focus:outline-none transition cursor-pointer"
            >
              {isRegistering ? "Inicia sesión" : "Regístrate ahora"}
            </button>
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <div className="rounded-md shadow-sm space-y-4">
            <div>
              <label className="text-xs text-gray-400 font-semibold mb-1 block">Correo Electrónico</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#161f38] border border-[#2d3a5f] rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition"
                placeholder="nombre@correo.com"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 font-semibold mb-1 block">Contraseña</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[#161f38] border border-[#2d3a5f] rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition"
                placeholder="••••••••"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={submitLoading}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-semibold rounded-xl text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 focus:outline-none shadow-lg shadow-blue-500/20 transition cursor-pointer disabled:opacity-55"
            >
              {submitLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : isRegistering ? (
                "Registrarse"
              ) : (
                "Ingresar"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
