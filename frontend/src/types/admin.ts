export interface DashboardStats {
  users: {
    total: number;
    customers: number;
    agents: number;
    admins: number;
    new_this_week: number;
  };
  conversations: {
    total: number;
    active: number;
    total_messages: number;
    avg_messages_per_conversation: number;
    new_this_week: number;
  };
  documents: {
    total: number;
    processed: number;
    processing_rate: number;
  };
  knowledge_bases: {
    total: number;
    active: number;
  };
  tools: {
    total: number;
    active: number;
    total_executions: number;
    success_rate: number;
  };
}

export interface ActivityChartData {
  users: { date: string; count: number }[];
  conversations: { date: string; count: number }[];
  messages: { date: string; count: number }[];
}

export interface AIUsageData {
  models: {
    model: string;
    requests: number;
    total_tokens: number;
    avg_response_time_ms: number;
  }[];
  tools: {
    name: string;
    category: string;
    executions: number;
    avg_execution_time_ms: number;
  }[];
}

export interface SystemConfig {
  environment: string;
  version: string;
  api_prefix: string;
  openai_model: string;
  embedding_model: string;
  rate_limit: string;
  vector_search: {
    top_k: number;
    similarity_threshold: number;
  };
  conversation_memory_window: number;
  allowed_file_types: string[];
  max_file_size_mb: number;
}

export interface AdminUser {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: 'admin' | 'support_agent' | 'customer';
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}