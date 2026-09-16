export interface Agent {
  id: string;
  name: string;
  description?: string | null;
  provider: string;
  model: string;
  system_prompt: string;
  temperature: number;
  max_tokens: number;
  status?: string;
  notification_phone: string | null;
  custom_fields: any; // Can be array of fields or stringified JSON
  channels?: string[];
  whatsapp_connected?: boolean;
  whatsapp_phone_number_id?: string | null;
  google_calendar_client_id?: string | null;
  google_calendar_connected?: boolean;
  google_calendar_email?: string | null;
  // Wasi.co Integration
  wasi_company_id?: string | null;
  wasi_connected?: boolean;
  wasi_sync_status?: string;
  wasi_last_sync_at?: string | null;
  wasi_properties_count?: number;
  stt_provider?: string;
  timezone?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Message {
  id?: string;
  conversation_id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sent_at: string;
}

export interface Conversation {
  id?: string;
  agent_id?: string;
  contact_name: string | null;
  contact_phone?: string | null;
  channel?: 'web' | 'whatsapp';
  status: 'active' | 'handoff' | 'inactive' | 'closed';
  last_message?: string;
  last_message_at?: string;
  created_at?: string;
  lead_notified?: boolean;
  agent_name?: string;
  agent?: { id?: string; name?: string };
  message_count?: number;
  started_at?: string;
}

export interface Lead {
  id?: string;
  agent_id?: string;
  conversation_id?: string | null;
  name: string | null;
  phone?: string | null;
  email?: string | null;
  status?: 'primer_contacto' | 'en_cualificacion' | 'cualificado' | 'objetivo_cumplido' | 'perdido' | string;
  custom_data?: Record<string, any> | null;
  created_at?: string;
  updated_at?: string;
  agent_name?: string;
  source_channel?: string;
  captured_at?: string;
}

export interface PreloadedContact {
  id: string;
  agent_id: string;
  name: string;
  phone: string;
  email?: string | null;
  notes?: string | null;
  custom_data?: Record<string, any> | null;
  created_at?: string;
  source?: string;
  nickname?: string | null;
  ai_category?: string | null;
  ai_confidence?: number | null;
  ai_analysis?: any;
  whatsapp_chat_id?: string | null;
  last_message_preview?: string | null;
}

export interface BusinessContext {
  business_name: string;
  business_type: string;
  products_services?: string;
  ideal_client?: string;
  sale_keywords?: string[];
  personal_keywords?: string[];
  additional_notes?: string;
}

export interface WhatsAppContact {
  chat_id: string;
  name: string;
  phone: string;
  last_message: string;
  last_message_at: string;
  message_count: number;
  is_group: boolean;
}

export interface DiagnosticResult {
  contact: WhatsAppContact;
  category: 'cliente_potencial' | 'cliente_existente' | 'aliado_estrategico' | 'personal' | 'proveedor' | 'irrelevante';
  confidence: number;
  reason: string;
  nickname: string | null;
  business_data?: {
    interest?: string;
    budget?: string;
    last_purchase?: string;
    interaction_summary?: string;
  };
  suggested_crm_stage: string;
}

export interface DiagnosticStatus {
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress: number;
  current_chat?: string;
  total_chats: number;
  analyzed_chats: number;
  estimated_remaining_seconds: number;
  results?: DiagnosticResult[];
}


export interface AgentImage {
  id: string;
  agent_id: string;
  filename: string;
  description: string | null;
  url: string;
  uploaded_at: string;
}

export type KbImage = AgentImage;

export interface KbDocument {
  id: string;
  agent_id: string;
  filename: string;
  content_type?: string;
  chunk_count?: number;
  content?: string;
  uploaded_at: string;
}

export interface AgentUsage {
  id: string;
  agent_id: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost: number;
  updated_at: string;
}

export interface DashboardMetrics {
  total_agents: number;
  total_conversations: number;
  total_leads: number;
  qualified_leads?: number;
  total_tokens_used?: number;
  total_cost_usd?: number;
  conversations_by_status?: Record<string, number>;
  leads_history?: Array<{ date: string; leads: number }>;
  recent_leads?: Lead[];
  recent_conversations?: Conversation[];
}

export interface UserProfile {
  id: string;
  email: string;
  role: "admin" | "user";
  status: "pending" | "active" | "rejected";
  assigned_agent_id?: string | null;
  assigned_agent?: {
    id: string;
    name: string;
    description?: string;
    provider?: string;
    model?: string;
  } | null;
  created_at?: string;
  approved_at?: string;
  approved_by?: string;
}

export const ADMIN_EMAILS = [
  "alejandr.ia.8725@gmail.com",
  "conecta@genia.com.co",
  "alejandro_baena@hotmail.com"
];

export function checkIsAdmin(userEmail?: string | null, role?: string | null): boolean {
  if (role === "admin") return true;
  if (!userEmail) return false;
  return ADMIN_EMAILS.includes(userEmail.toLowerCase().trim());
}
