import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { formatRelativeTime, cn } from '@/utils/helpers';
import {
  Plus,
  Search,
  Database,
  MoreVertical,
  Trash2,
  Edit2,
  Users,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Archive,
  FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DropdownMenu, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/Dropdown';
import { ScrollArea } from '@/components/ui/ScrollArea';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

interface KnowledgeBase {
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

interface KnowledgeBaseDocument {
  id: string;
  knowledge_base_id: string;
  document_id: string;
  added_at: string;
  document?: {
    id: string;
    original_filename: string;
    status: string;
    chunk_count: number;
  };
}

interface KBsResponse {
  knowledge_bases: KnowledgeBase[];
  total: number;
}

interface KBDocsResponse {
  documents: KnowledgeBaseDocument[];
  total: number;
}

async function fetchKnowledgeBases(): Promise<KBsResponse> {
  const response = await api.get('/chat/knowledge-bases');
  return { knowledge_bases: response.data, total: response.data.length };
}

async function fetchKBDocuments(kbId: string): Promise<KBDocsResponse> {
  const response = await api.get(`/chat/knowledge-bases/${kbId}/documents`);
  return { documents: response.data, total: response.data.length };
}

async function createKB(data: {
  name: string;
  description?: string;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  top_k?: number;
  similarity_threshold?: number;
}): Promise<KnowledgeBase> {
  const response = await api.post('/chat/knowledge-bases', data);
  return response.data;
}

async function updateKB(id: string, data: Partial<KnowledgeBase>): Promise<KnowledgeBase> {
  const response = await api.patch(`/chat/knowledge-bases/${id}`, data);
  return response.data;
}

async function deleteKB(id: string): Promise<void> {
  await api.delete(`/chat/knowledge-bases/${id}`);
}

async function addDocumentToKB(kbId: string, documentId: string): Promise<void> {
  await api.post(`/chat/knowledge-bases/${kbId}/documents`, { document_id: documentId });
}

async function removeDocumentFromKB(kbId: string, documentId: string): Promise<void> {
  await api.delete(`/chat/knowledge-bases/${kbId}/documents/${documentId}`);
}

async function fetchAvailableDocuments(): Promise<Array<{ id: string; original_filename: string; status: string }>> {
  const response = await api.get('/chat/documents', { params: { status: 'completed', limit: 100 } });
  return response.data;
}

const kbSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  description: z.string().optional(),
  embedding_model: z.string().default('text-embedding-3-large'),
  chunk_size: z.number().min(100).max(5000).default(1000),
  chunk_overlap: z.number().min(0).max(1000).default(200),
  top_k: z.number().min(1).max(20).default(5),
  similarity_threshold: z.number().min(0).max(1).default(0.7),
});

type KBFormData = z.infer<typeof kbSchema>;

function getStatusBadge(status: KnowledgeBase['status']) {
  switch (status) {
    case 'active': return <Badge variant="success"><CheckCircle className="h-3 w-3 mr-1" /> Active</Badge>;
    case 'inactive': return <Badge variant="warning"><Clock className="h-3 w-3 mr-1" /> Inactive</Badge>;
    case 'archived': return <Badge variant="neutral"><Archive className="h-3 w-3 mr-1" /> Archived</Badge>;
  }
}

export function KnowledgeBasesPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [editingKB, setEditingKB] = useState<KnowledgeBase | null>(null);
  const [viewingKB, setViewingKB] = useState<KnowledgeBase | null>(null);
  const [kbDocs, setKbDocs] = useState<KnowledgeBaseDocument[]>([]);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<KBFormData>({
    resolver: zodResolver(kbSchema),
    defaultValues: {
      name: '',
      description: '',
      embedding_model: 'text-embedding-3-large',
      chunk_size: 1000,
      chunk_overlap: 200,
      top_k: 5,
      similarity_threshold: 0.7,
    },
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: fetchKnowledgeBases,
  });

  const createMutation = useMutation({
    mutationFn: createKB,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      setIsCreating(false);
      reset();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<KnowledgeBase> }) => updateKB(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      setEditingKB(null);
      reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteKB,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] }),
  });

  const addDocMutation = useMutation({
    mutationFn: ({ kbId, documentId }: { kbId: string; documentId: string }) => addDocumentToKB(kbId, documentId),
    onSuccess: () => {
      if (viewingKB) {
        fetchKBDocuments(viewingKB.id).then(res => setKbDocs(res.documents));
      }
    },
  });

  const removeDocMutation = useMutation({
    mutationFn: ({ kbId, documentId }: { kbId: string; documentId: string }) => removeDocumentFromKB(kbId, documentId),
    onSuccess: () => {
      if (viewingKB) {
        fetchKBDocuments(viewingKB.id).then(res => setKbDocs(res.documents));
      }
    },
  });

  const onSubmit = (data: KBFormData) => {
    if (editingKB) {
      updateMutation.mutate({ id: editingKB.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEdit = (kb: KnowledgeBase) => {
    reset({
      name: kb.name,
      description: kb.description || '',
      embedding_model: kb.embedding_model,
      chunk_size: kb.chunk_size,
      chunk_overlap: kb.chunk_overlap,
      top_k: kb.top_k,
      similarity_threshold: kb.similarity_threshold,
    });
    setEditingKB(kb);
  };

  const handleView = async (kb: KnowledgeBase) => {
    setViewingKB(kb);
    const res = await fetchKBDocuments(kb.id);
    setKbDocs(res.documents);
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this knowledge base?')) {
      deleteMutation.mutate(id);
    }
  };

  const filteredKBs = data?.knowledge_bases.filter((kb) =>
    kb.name.toLowerCase().includes(search.toLowerCase())
  ) || [];

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Knowledge Bases</h1>
          <p className="text-neutral-500 dark:text-neutral-400">Manage your RAG knowledge bases</p>
        </div>
        <Button onClick={() => { reset(); setIsCreating(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          New Knowledge Base
        </Button>
      </div>

      {(isCreating || editingKB) && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>{editingKB ? 'Edit' : 'Create'} Knowledge Base</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Input
                  label="Name"
                  placeholder="My Knowledge Base"
                  {...register('name')}
                  error={errors.name?.message}
                />
                <Input
                  label="Embedding Model"
                  placeholder="text-embedding-3-large"
                  {...register('embedding_model')}
                />
              </div>
              <Input
                label="Description"
                placeholder="Optional description..."
                {...register('description')}
                className="md:col-span-2"
              />
              <div className="grid gap-4 md:grid-cols-4">
                <Input
                  label="Chunk Size"
                  type="number"
                  {...register('chunk_size', { valueAsNumber: true })}
                  error={errors.chunk_size?.message}
                />
                <Input
                  label="Chunk Overlap"
                  type="number"
                  {...register('chunk_overlap', { valueAsNumber: true })}
                  error={errors.chunk_overlap?.message}
                />
                <Input
                  label="Top K"
                  type="number"
                  {...register('top_k', { valueAsNumber: true })}
                  error={errors.top_k?.message}
                />
                <Input
                  label="Similarity Threshold"
                  type="number"
                  step="0.1"
                  {...register('similarity_threshold', { valueAsNumber: true })}
                  error={errors.similarity_threshold?.message}
                />
              </div>
              <CardFooter className="flex justify-end gap-2 pt-0">
                <Button variant="outline" type="button" onClick={() => { setIsCreating(false); setEditingKB(null); reset(); }}>
                  Cancel
                </Button>
                <Button type="submit" loading={isSubmitting || createMutation.isPending || updateMutation.isPending}>
                  {editingKB ? 'Save' : 'Create'}
                </Button>
              </CardFooter>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col lg:flex-row gap-6 flex-1">
        <div className="lg:w-80 flex-shrink-0">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Search className="h-4 w-4 text-neutral-400" />
                <Input
                  placeholder="Search knowledge bases..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="flex-1 bg-transparent border-0 p-0 focus:ring-0"
                />
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="max-h-[calc(100vh-300px)]">
                {isLoading ? (
                  <div className="p-4 space-y-3">
                    {[...Array(5)].map((_, i) => (
                      <div key={i} className="animate-pulse h-20 bg-neutral-200 dark:bg-neutral-800 rounded-lg" />
                    ))}
                  </div>
                ) : filteredKBs.length === 0 ? (
                  <div className="p-8 text-center">
                    <Database className="h-12 w-12 text-neutral-300 dark:text-neutral-700 mx-auto mb-3" />
                    <p className="text-neutral-500 dark:text-neutral-400">No knowledge bases found</p>
                    <p className="text-sm text-neutral-400 dark:text-neutral-500 mt-1">
                      {search ? 'Try a different search term' : 'Create your first knowledge base'}
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
                    {filteredKBs.map((kb) => (
                      <button
                        key={kb.id}
                        onClick={() => handleView(kb)}
                        className={cn(
                          'w-full p-4 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors flex items-start gap-3',
                          viewingKB?.id === kb.id && 'bg-primary-50 dark:bg-primary-900/20',
                          'group'
                        )}
                      >
                        <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                          <Database className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-neutral-900 dark:text-neutral-100 truncate">
                            {kb.name}
                          </p>
                          <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
                            {kb.description || 'No description'}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            {getStatusBadge(kb.status)}
                            <span className="text-xs text-neutral-400 dark:text-neutral-500">
                              {kb.document_count || 0} docs
                            </span>
                          </div>
                        </div>
                        <DropdownMenu align="right">
                          <Button variant="ghost" size="sm" className="p-1 opacity-0 group-hover:opacity-100">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                          <DropdownMenuItem icon={<Edit2 className="h-4 w-4" />} onClick={() => handleEdit(kb)}>
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem icon={<Users className="h-4 w-4" />} onClick={() => handleView(kb)}>
                            Manage Documents
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem icon={<Trash2 className="h-4 w-4" />} destructive onClick={() => handleDelete(kb.id)}>
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenu>
                      </button>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        <div className="flex-1">
          {viewingKB ? (
            <Card className="h-[calc(100vh-180px)] flex flex-col">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{viewingKB.name}</CardTitle>
                    <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                      {viewingKB.description || 'No description'}
                    </p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => { setViewingKB(null); setKbDocs([]); }}>
                    <Users className="h-4 w-4 mr-2" />
                    Add Documents
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="flex-1 overflow-y-auto">
                {kbDocs.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center p-8 text-center">
                    <Database className="h-12 w-12 text-neutral-300 dark:text-neutral-700 mb-3" />
                    <h3 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-1">No documents added</h3>
                    <p className="text-neutral-500 dark:text-neutral-400 mb-4">Add documents to this knowledge base to enable RAG</p>
                    <Button variant="outline" size="sm" onClick={() => { setViewingKB(null); setKbDocs([]); }}>
                      <Users className="h-4 w-4 mr-2" />
                      Add Documents
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {kbDocs.map((doc) => (
                      <div key={doc.id} className="flex items-center justify-between p-3 rounded-lg border border-neutral-200 dark:border-neutral-800">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
                            <FileText className="h-5 w-5 text-blue-500" />
                          </div>
                          <div>
                            <p className="font-medium text-neutral-900 dark:text-neutral-100 truncate max-w-xs">
                              {doc.document?.original_filename || 'Unknown'}
                            </p>
                            <p className="text-xs text-neutral-500 dark:text-neutral-400">
                              {doc.document?.chunk_count || 0} chunks • {doc.document?.status || 'unknown'}
                            </p>
                          </div>
                        </div>
                        <DropdownMenu align="right">
                          <Button variant="ghost" size="sm" className="p-1">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                          <DropdownMenuItem
                            icon={<Trash2 className="h-4 w-4" />}
                            destructive
                            onClick={() => removeDocMutation.mutate({ kbId: viewingKB!.id, documentId: doc.document_id })}
                          >
                            Remove
                          </DropdownMenuItem>
                        </DropdownMenu>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="h-[calc(100vh-180px)] flex flex-col">
              <CardHeader>
                <CardTitle>Select a Knowledge Base</CardTitle>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                  Click on a knowledge base from the sidebar to manage its documents and settings.
                </p>
              </CardHeader>
              <CardContent className="flex-1 flex items-center justify-center">
                <div className="text-center p-8">
                  <Database className="h-16 w-16 text-neutral-300 dark:text-neutral-700 mx-auto mb-4" />
                  <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                    Knowledge Base Management
                  </h2>
                  <p className="text-neutral-500 dark:text-neutral-400 max-w-md">
                    Create knowledge bases to organize your documents for RAG-powered conversations.
                    Each knowledge base can have its own embedding model, chunking strategy, and search parameters.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}