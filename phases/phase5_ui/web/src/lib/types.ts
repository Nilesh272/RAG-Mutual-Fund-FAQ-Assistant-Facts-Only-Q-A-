export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  citation?: string;
  intent?: string;
  timestamp: string;
}

export interface ChatResponse {
  thread_id: string;
  answer: string;
  citation: string;
  last_updated: string | null;
  intent: string;
  formatted_answer?: string;
}

export interface ThreadResponse {
  thread_id: string;
  messages: ChatMessage[];
  scheme_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface HealthResponse {
  status: string;
  indexed_chunks: number;
  collection: string;
}
