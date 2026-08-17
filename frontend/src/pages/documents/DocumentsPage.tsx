import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { formatRelativeTime, formatFileSize, cn } from '@/utils/helpers';
import {
  Upload,
  FileText,
  Search,
  Filter,
  MoreVertical,
  Trash2,
  Download,
  Eye,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DropdownMenu, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/Dropdown';
import { ScrollArea } from '@/components/ui/ScrollArea';

interface Document {
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

interface DocumentsResponse {
  documents: Document[];
  total: number;
}

async function fetchDocuments(params: { skip?: number; limit?: number; status?: string }): Promise<DocumentsResponse> {
  const response = await api.get('/chat/documents', { params });
  return { documents: response.data, total: response.data.length };
}

async function uploadDocument(file: File): Promise<{ document_id: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/chat/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

async function processDocument(documentId: string): Promise<Document> {
  const response = await api.post(`/chat/documents/${documentId}/process`);
  return response.data;
}

async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/chat/documents/${documentId}`);
}

const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
  'text/html',
];

const MAX_FILE_SIZE = 10 * 1024 * 1024;

function getStatusBadge(status: Document['status']) {
  switch (status) {
    case 'completed': return <Badge variant="success"><CheckCircle className="h-3 w-3 mr-1" /> Completed</Badge>;
    case 'processing': return <Badge variant="primary"><Loader2 className="h-3 w-3 mr-1 animate-spin" /> Processing</Badge>;
    case 'pending': return <Badge variant="warning"><Clock className="h-3 w-3 mr-1" /> Pending</Badge>;
    case 'failed': return <Badge variant="destructive"><AlertCircle className="h-3 w-3 mr-1" /> Failed</Badge>;
  }
}

function getFileIcon(type: Document['document_type']) {
  switch (type) {
    case 'pdf': return <FileText className="h-5 w-5 text-red-500" />;
    case 'docx': return <FileText className="h-5 w-5 text-blue-500" />;
    case 'txt': return <FileText className="h-5 w-5 text-neutral-500" />;
    case 'markdown': return <FileText className="h-5 w-5 text-green-500" />;
    case 'html': return <FileText className="h-5 w-5 text-orange-500" />;
  }
}

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'processing' | 'completed' | 'failed'>('all');
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['documents', search, statusFilter],
    queryFn: () => fetchDocuments({ skip: 0, limit: 50, status: statusFilter !== 'all' ? statusFilter : undefined }),
  });

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setUploadProgress({});
    },
  });

  const processMutation = useMutation({
    mutationFn: processDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  });

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFiles(files);
    e.target.value = '';
  };

  const handleFiles = (files: File[]) => {
    files.forEach((file) => {
      if (!ALLOWED_TYPES.includes(file.type)) {
        alert(`File type not allowed: ${file.type}`);
        return;
      }
      if (file.size > MAX_FILE_SIZE) {
        alert(`File too large: ${file.name} (max 10MB)`);
        return;
      }
      setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));
      uploadMutation.mutate(file);
    });
  };

  const filteredDocuments = data?.documents.filter((d) =>
    d.original_filename.toLowerCase().includes(search.toLowerCase())
  ) || [];

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Documents</h1>
          <p className="text-neutral-500 dark:text-neutral-400">Upload and manage your knowledge base documents</p>
        </div>
        <div className="relative">
          <input
            type="file"
            id="file-upload"
            multiple
            accept={ALLOWED_TYPES.join(',')}
            onChange={handleFileSelect}
            className="hidden"
          />
          <Button variant="outline" onClick={() => document.getElementById('file-upload')?.click()}>
            <Upload className="h-4 w-4 mr-2" />
            Upload Document
          </Button>
        </div>
      </div>

      <div
        className={cn(
          'mb-6 p-6 border-2 border-dashed rounded-xl text-center transition-colors',
          dragActive
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-neutral-300 dark:border-neutral-700 hover:border-primary-500'
        )}
        onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
        onDragOver={(e) => { e.preventDefault(); }}
        onDrop={handleDrop}
      >
        <Upload className="h-12 w-12 text-neutral-300 dark:text-neutral-600 mx-auto mb-3" />
        <p className="text-neutral-600 dark:text-neutral-400">
          Drag and drop files here, or click to browse
        </p>
        <p className="text-sm text-neutral-400 dark:text-neutral-500 mt-1">
          Supported: PDF, DOCX, TXT, Markdown, HTML (max 10MB each)
        </p>
      </div>

      {Object.keys(uploadProgress).length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Uploading...</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(uploadProgress).map(([filename, progress]) => (
                <div key={filename} className="flex items-center gap-3">
                  <div className="flex-1 h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-600 transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <span className="text-sm text-neutral-600 dark:text-neutral-400 w-16 text-right">
                    {progress}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        <div className="lg:w-80 flex-shrink-0">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Search className="h-4 w-4 text-neutral-400" />
                <Input
                  placeholder="Search documents..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="flex-1 bg-transparent border-0 p-0 focus:ring-0"
                />
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="border-t border-neutral-200 dark:border-neutral-800">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
                  className="w-full px-4 py-2 text-sm bg-transparent border-0 focus:outline-none focus:ring-0"
                >
                  <option value="all">All Status</option>
                  <option value="pending">Pending</option>
                  <option value="processing">Processing</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
              <ScrollArea className="max-h-[calc(100vh-300px)]">
                {isLoading ? (
                  <div className="p-4 space-y-3">
                    {[...Array(5)].map((_, i) => (
                      <div key={i} className="animate-pulse h-20 bg-neutral-200 dark:bg-neutral-800 rounded-lg" />
                    ))}
                  </div>
                ) : filteredDocuments.length === 0 ? (
                  <div className="p-8 text-center">
                    <FileText className="h-12 w-12 text-neutral-300 dark:text-neutral-700 mx-auto mb-3" />
                    <p className="text-neutral-500 dark:text-neutral-400">No documents found</p>
                    <p className="text-sm text-neutral-400 dark:text-neutral-500 mt-1">
                      {search ? 'Try a different search term' : 'Upload your first document'}
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
                    {filteredDocuments.map((doc) => (
                      <div key={doc.id} className="p-4 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors">
                        <div className="flex items-start gap-3">
                          <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
                            {getFileIcon(doc.document_type)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-neutral-900 dark:text-neutral-100 truncate">
                              {doc.original_filename}
                            </p>
                            <div className="flex items-center gap-2 mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                              <span>{formatFileSize(doc.file_size)}</span>
                              <span>•</span>
                              <span>{doc.chunk_count} chunks</span>
                              {doc.page_count && <>• <span>{doc.page_count} pages</span></>}
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                              {getStatusBadge(doc.status)}
                            </div>
                          </div>
                          <DropdownMenu align="right">
                            <Button variant="ghost" size="sm" className="p-1">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                            {doc.status === 'pending' || doc.status === 'failed' ? (
                              <DropdownMenuItem
                                icon={<Loader2 className="h-4 w-4" />}
                                onClick={() => processMutation.mutate(doc.id)}
                                disabled={processMutation.isPending}
                              >
                                Process
                              </DropdownMenuItem>
                            ) : null}
                            <DropdownMenuItem icon={<Eye className="h-4 w-4" />} onClick={() => {}}>View</DropdownMenuItem>
                            <DropdownMenuItem icon={<Download className="h-4 w-4" />} onClick={() => {}}>Download</DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem icon={<Trash2 className="h-4 w-4" />} destructive onClick={() => deleteMutation.mutate(doc.id)}>
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenu>
                        </div>
                        {doc.error_message && (
                          <div className="mt-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                            <p className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1">
                              <AlertCircle className="h-4 w-4" />
                              {doc.error_message}
                            </p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        <div className="flex-1">
          <Card className="h-[calc(100vh-180px)] flex flex-col">
            <CardHeader>
              <CardTitle>Document Details</CardTitle>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                Select a document from the sidebar to view details and manage processing.
              </p>
            </CardHeader>
            <CardContent className="flex-1 flex items-center justify-center">
              <div className="text-center p-8">
                <FileText className="h-16 w-16 text-neutral-300 dark:text-neutral-700 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                  No document selected
                </h2>
                <p className="text-neutral-500 dark:text-neutral-400">
                  Click on a document in the sidebar to view its details, chunks, and processing status.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}