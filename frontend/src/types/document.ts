export interface Document {
  id: string;
  user_id: string;
  filename: string;
  original_filename: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  document_type: 'pdf' | 'docx' | 'txt' | 'markdown' | 'html';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  page_count?: number;
  chunk_count: number;
  error_message?: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  processed_at?: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'inactive' | 'archived';
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  similarity_threshold: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  document_count?: number;
}

export interface CreateKnowledgeBaseRequest {
  name: string;
  description?: string;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  top_k?: number;
  similarity_threshold?: number;
}

export interface UpdateKnowledgeBaseRequest {
  name?: string;
  description?: string;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  top_k?: number;
  similarity_threshold?: number;
  status?: 'active' | 'inactive' | 'archived';
}

export interface KnowledgeBaseDocument {
  id: string;
  knowledge_base_id: string;
  document_id: string;
  added_at: string;
  document?: Document;
}