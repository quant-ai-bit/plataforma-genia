import { supabase } from "./supabase";

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL !== undefined && process.env.NEXT_PUBLIC_API_URL !== "") {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
    return "";
  }
  return "http://127.0.0.1:8000";
}

const API_BASE_URL = getApiBaseUrl();

/**
 * Obtiene las cabeceras de autenticación con el token JWT de Supabase actual.
 */
export async function getAuthHeader(): Promise<Record<string, string>> {
  if (!supabase) return {};
  
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      return {
        Authorization: `Bearer ${session.access_token}`,
      };
    }
  } catch (error) {
    console.error("Error al obtener la sesión de Supabase:", error);
  }
  
  return {};
}

/**
 * Wrapper de fetch que inyecta automáticamente el token JWT en la cabecera Authorization.
 */
export async function authenticatedFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${API_BASE_URL}${path.startsWith('/') ? path : '/' + path}`;
  
  const authHeader = await getAuthHeader();
  
  const headers: Record<string, string> = {
    ...authHeader,
    ...(options.headers as Record<string, string>),
  };
  
  // Si no se especifica Content-Type y enviamos un JSON stringify, lo agregamos automáticamente
  if (
    options.body &&
    typeof options.body === "string" &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] = "application/json";
  }
  
  return fetch(url, {
    ...options,
    headers,
  });
}
