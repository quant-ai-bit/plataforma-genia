"use client";

import { useState, useEffect } from "react";
import { supabase, isSupabaseConfigured } from "../lib/supabase";
import { User } from "@supabase/supabase-js";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!isSupabaseConfigured) {
      setLoading(false);
      return;
    }

    // Get initial session
    supabase!.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(session.user);
        setToken(session.access_token);
      }
      setLoading(false);
    }).catch((error) => {
      console.error("Error al obtener sesión de Supabase:", error);
      setLoading(false);
    });

    // Listen for auth state changes
    const { data: { subscription } } = supabase!.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setUser(session.user);
        setToken(session.access_token);
      } else {
        setUser(null);
        setToken("");
      }
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const logout = async () => {
    if (isSupabaseConfigured && supabase) {
      setLoading(true);
      try {
        await supabase.auth.signOut();
      } catch (err) {
        console.error("Error al cerrar sesión:", err);
      } finally {
        setLoading(false);
      }
    }
  };

  return {
    user,
    token,
    loading,
    logout,
    isConfigured: isSupabaseConfigured,
  };
}
