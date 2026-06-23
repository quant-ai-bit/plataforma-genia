export interface Agent {
  id: string;
  name: string;
  provider: string;
  model: string;
  system_prompt: string;
  temperature: number;
  max_tokens: number;
  notification_phone: string | null;
  custom_fields: any; // Can be array of fields or stringified JSON
  created_at?: string;
  updated_at?: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sent_at: string;
}

export interface Conversation {
  id: string;
  agent_id: string;
  contact_name: string | null;
  contact_phone: string | null;
  channel: 'web' | 'whatsapp';
  status: 'active' | 'handoff' | 'inactive';
  last_message_at: string;
  created_at: string;
  lead_notified?: boolean;
}

export interface Lead {
  id: string;
  agent_id: string;
  conversation_id: string | null;
  name: string | null;
  phone: string | null;
  email: string | null;
  status: 'pending' | 'qualified' | 'contacted' | 'lost';
  custom_data: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface AgentImage {
  id: string;
  agent_id: string;
  filename: string;
  description: string | null;
  url: string;
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
  qualified_leads: number;
  total_tokens_used: number;
  total_cost_usd: number;
}
