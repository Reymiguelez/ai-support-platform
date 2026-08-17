export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  status: 'active' | 'archived' | 'closed';
  model: string;
  temperature: number;
  system_prompt?: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  message_count?: number;
  last_message?: Message;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tokens: number;
  model?: string;
  execution_time_ms?: number;
  tool_calls: ToolCall[];
  tool_results: ToolResult[];
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ToolCall {
  id: string;
  type: 'function';
  function: {
    name: string;
    arguments: string;
  };
}

export interface ToolResult {
  tool_call_id: string;
  name: string;
  result?: unknown;
  error?: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  use_rag?: boolean;
  knowledge_base_id?: string;
  use_tools?: boolean;
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
  message_id?: string;
}

export interface CreateConversationRequest {
  title?: string;
  system_prompt?: string;
  model?: string;
  temperature?: number;
}

export interface UpdateConversationRequest {
  title?: string;
  system_prompt?: string;
  model?: string;
  temperature?: number;
  status?: 'active' | 'archived' | 'closed';
}