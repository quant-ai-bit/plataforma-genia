"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User } from "@supabase/supabase-js";
import { supabase, isSupabaseConfigured } from "./supabase";
import { authenticatedFetch, getApiBaseUrl } from "./api";
import { Agent, Lead } from "./types";

const API_BASE_URL = getApiBaseUrl();

interface AppContextType {
  user: User | null;
  token: string;
  authLoading: boolean;
  logout: () => Promise<void>;
  isSupabaseConfigured: boolean;
  isBackendOnline: boolean | null;
  setIsBackendOnline: (status: boolean | null) => void;
  checkHealthAndLoadData: () => Promise<void>;
  agents: Agent[];
  setAgents: React.Dispatch<React.SetStateAction<Agent[]>>;
  leads: Lead[];
  setLeads: React.Dispatch<React.SetStateAction<Lead[]>>;
  availableModels: {
    groq: string[];
    gemini: string[];
    openrouter?: string[];
  };
  setAvailableModels: React.Dispatch<React.SetStateAction<{ groq: string[]; gemini: string[]; openrouter?: string[] }>>;
  agentUsages: Record<string, any[]>;
  setAgentUsages: React.Dispatch<React.SetStateAction<Record<string, any[]>>>;
  loadAgentUsage: (agentId: string) => Promise<void>;
  loadBackendData: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string>("");
  const [authLoading, setAuthLoading] = useState<boolean>(true);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [agentUsages, setAgentUsages] = useState<Record<string, any[]>>({});
  const [availableModels, setAvailableModels] = useState<{ groq: string[]; gemini: string[]; openrouter?: string[] }>({
    groq: [],
    gemini: [],
    openrouter: []
  });

  const logout = async () => {
    if (isSupabaseConfigured && supabase) {
      setAuthLoading(true);
      try {
        await supabase.auth.signOut();
      } catch (err) {
        console.error("Error al cerrar sesión:", err);
      } finally {
        setAuthLoading(false);
      }
    }
  };

  const loadAgentUsage = async (agentId: string) => {
    try {
      const res = await authenticatedFetch(`/api/agents/${agentId}/usage`);
      if (res.ok) {
        const data = await res.json();
        setAgentUsages(prev => ({ ...prev, [agentId]: data }));
      }
    } catch (err) {
      console.error(`Error al cargar consumos para el agente ${agentId}:`, err);
    }
  };

  const loadBackendData = async () => {
    try {
      // 1. Obtener Modelos
      const resModels = await authenticatedFetch(`/api/models`);
      if (resModels.ok) {
        const m = await resModels.json();
        setAvailableModels(m);
      }
      
      // 2. Obtener Agentes
      const resAgents = await authenticatedFetch(`/api/agents`);
      if (resAgents.ok) {
        const a = await resAgents.json();
        setAgents(a);
        // Cargar consumos de cada agente
        a.forEach((agent: any) => {
          loadAgentUsage(agent.id);
        });
      }

      // 3. Obtener Leads
      const resLeads = await authenticatedFetch(`/api/leads`);
      if (resLeads.ok) {
        const l = await resLeads.json();
        setLeads(l);
      }
    } catch (err) {
      console.error("Error al cargar datos del servidor backend: ", err);
    }
  };

  const loadMockData = () => {
    const mockAgents: Agent[] = [
      {
        id: "mock-1",
        name: "Genia Agente Inmobiliario",
        provider: "groq",
        model: "llama-3.3-70b-versatile",
        system_prompt: "Eres un agente inmobiliario de GENIA...",
        temperature: 0.2,
        max_tokens: 1024,
        notification_phone: "+573001234567",
        custom_fields: [
          { key: "presupuesto", label: "Presupuesto aproximado", type: "string", required: true },
          { key: "zona", label: "Zona de interés", type: "string", required: true }
        ],
        created_at: new Date().toISOString()
      },
      {
        id: "mock-2",
        name: "Genia Asistente Soporte TI",
        provider: "groq",
        model: "llama-3.1-8b-instant",
        system_prompt: "Eres un asistente de soporte TI...",
        temperature: 0.5,
        max_tokens: 512,
        notification_phone: null,
        custom_fields: [
          { key: "sistema_operativo", label: "Sistema Operativo", type: "string", required: false },
          { key: "descripcion_error", label: "Descripción del Error", type: "string", required: true }
        ],
        created_at: new Date().toISOString()
      }
    ];

    const mockLeads: Lead[] = [
      {
        id: "mock-lead-1",
        agent_id: "mock-1",
        conversation_id: "conv-1",
        name: "Juan Pérez",
        phone: "+573001234567",
        email: "juan@perez.com",
        status: "qualified",
        custom_data: { presupuesto: "$150,000,000 COP", zona: "El Poblado" },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: "mock-lead-2",
        agent_id: "mock-2",
        conversation_id: "conv-2",
        name: "María Gómez",
        phone: "+34600123456",
        email: "maria@gomez.com",
        status: "qualified",
        custom_data: { sistema_operativo: "Windows 11", descripcion_error: "Pantalla azul al iniciar" },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    ];

    setAgents(mockAgents);
    setLeads(mockLeads);
    setAvailableModels({
      groq: ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"],
      gemini: ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
      openrouter: ["deepseek/deepseek-chat", "anthropic/claude-3.5-sonnet:beta", "google/gemini-2.5-flash", "openai/gpt-4o-mini", "openai/gpt-4o"]
    });
    setAgentUsages({
      "mock-1": [
        { id: "u-1", agent_id: "mock-1", model: "llama-3.3-70b-versatile", prompt_tokens: 1250, completion_tokens: 340, total_tokens: 1590, cost: 0.0010066, last_used: new Date().toISOString() }
      ],
      "mock-2": [
        { id: "u-2", agent_id: "mock-2", model: "llama-3.1-8b-instant", prompt_tokens: 4200, completion_tokens: 1100, total_tokens: 5300, cost: 0.000298, last_used: new Date().toISOString() }
      ]
    });
  };

  const checkHealthAndLoadData = async () => {
    try {
      const res = await authenticatedFetch(`/`);
      if (res.ok) {
        setIsBackendOnline(true);
        await loadBackendData();
      } else {
        throw new Error("Offline");
      }
    } catch (err) {
      console.warn("Backend offline, cargando datos simulados.");
      setIsBackendOnline(false);
      loadMockData();
    }
  };

  // Auth Effects
  useEffect(() => {
    if (!isSupabaseConfigured) {
      setAuthLoading(false);
      checkHealthAndLoadData();
      return;
    }

    supabase!.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(session.user);
        setToken(session.access_token);
      }
      setAuthLoading(false);
    }).catch(() => {
      setAuthLoading(false);
    });

    const { data: { subscription } } = supabase!.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setUser(session.user);
        setToken(session.access_token);
      } else {
        setUser(null);
        setToken("");
      }
      setAuthLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Sync data on token/backend changes
  useEffect(() => {
    if (!isSupabaseConfigured || token) {
      checkHealthAndLoadData();
    }
  }, [token]);

  return (
    <AppContext.Provider
      value={{
        user,
        token,
        authLoading,
        logout,
        isSupabaseConfigured,
        isBackendOnline,
        setIsBackendOnline,
        checkHealthAndLoadData,
        agents,
        setAgents,
        leads,
        setLeads,
        availableModels,
        setAvailableModels,
        agentUsages,
        setAgentUsages,
        loadAgentUsage,
        loadBackendData
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return context;
}
