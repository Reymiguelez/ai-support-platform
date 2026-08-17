import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { formatRelativeTime, cn } from '@/utils/helpers';
import {
  Plus,
  Search,
  MoreVertical,
  Edit2,
  Archive,
  Star,
  Trash2,
  MessageSquare,
  Bot,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Avatar } from '@/components/ui/Avatar';
import { DropdownMenu, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/Dropdown';
import { ScrollArea } from '@/components/ui/ScrollArea';
import { useAuth } from '@/context/AuthContext';

interface Conversation {
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
  last_message?: {
    id: string;
    content: string;
    role: string;
    created_at: string;
  };
}

interface ConversationsResponse {
  conversations: Conversation[];
  total: number;
}

async function fetchConversations(params: { skip?: number; limit?: number; status?: string }): Promise<ConversationsResponse> {
  const response = await api.get('/chat/conversations', { params });
  return { conversations: response.data, total: response.data.length };
}

async function createConversation(data: { title: string }): Promise<Conversation> {
  const response = await api.post('/chat/conversations', data);
  return response.data;
}

async function updateConversation(id: string, data: Partial<Conversation>): Promise<Conversation> {
  const response = await api.patch(`/chat/conversations/${id}`, data);
  return response.data;
}

async function deleteConversation(id: string): Promise<void> {
  await api.delete(`/chat/conversations/${id}`);
}

export function ConversationsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'archived' | 'closed'>('all');
  const [isCreating, setIsCreating] = useState(false);
  const [newTitle, setNewTitle] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['conversations', search, statusFilter],
    queryFn: () => fetchConversations({
      skip: 0,
      limit: 50,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
  });

  const createMutation = useMutation({
    mutationFn: createConversation,
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      navigate(`/chat/${conversation.id}`);
      setIsCreating(false);
      setNewTitle('');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Conversation> }) => updateConversation(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conversations'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conversations'] }),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    createMutation.mutate({ title: newTitle });
  };

  const handleStatusChange = (conversation: Conversation, newStatus: Conversation['status']) => {
    updateMutation.mutate({ id: conversation.id, data: { status: newStatus } });
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this conversation?')) {
      deleteMutation.mutate(id);
    }
  };

  const filteredConversations = data?.conversations.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  ) || [];

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Conversations</h1>
          <p className="text-neutral-500 dark:text-neutral-400">Manage your chat conversations</p>
        </div>
        <Button onClick={() => setIsCreating(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Conversation
        </Button>
      </div>

      {isCreating && (
        <Card className="mb-6">
          <CardContent className="p-4">
            <form onSubmit={handleCreate} className="flex items-center gap-3">
              <Input
                placeholder="Conversation title..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="flex-1"
                autoFocus
              />
              <Button type="submit" loading={createMutation.isPending}>
                Create
              </Button>
              <Button variant="ghost" size="sm" onClick={() => { setIsCreating(false); setNewTitle(''); }}>
                Cancel
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        <aside className="lg:w-80 flex-shrink-0">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Search className="h-4 w-4 text-neutral-400" />
                <Input
                  placeholder="Search conversations..."
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
                  <option value="all">All</option>
                  <option value="active">Active</option>
                  <option value="archived">Archived</option>
                  <option value="closed">Closed</option>
                </select>
              </div>
              <ScrollArea className="max-h-[calc(100vh-300px)]">
                {isLoading ? (
                  <div className="p-4 space-y-3">
                    {[...Array(5)].map((_, i) => (
                      <div key={i} className="animate-pulse h-16 bg-neutral-200 dark:bg-neutral-800 rounded-lg" />
                    ))}
                  </div>
                ) : filteredConversations.length === 0 ? (
                  <div className="p-8 text-center">
                    <MessageSquare className="h-12 w-12 text-neutral-300 dark:text-neutral-700 mx-auto mb-3" />
                    <p className="text-neutral-500 dark:text-neutral-400">No conversations found</p>
                    <p className="text-sm text-neutral-400 dark:text-neutral-500 mt-1">
                      {search ? 'Try a different search term' : 'Start a new conversation'}
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
                    {filteredConversations.map((conversation) => (
                      <button
                        key={conversation.id}
                        onClick={() => navigate(`/chat/${conversation.id}`)}
                        className={cn(
                          'w-full p-4 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors flex items-start gap-3',
                          'group'
                        )}
                      >
                        <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                          <Bot className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-neutral-900 dark:text-neutral-100 truncate">
                            {conversation.title}
                          </p>
                          <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
                            {conversation.last_message?.content || 'No messages yet'}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge
                              variant={
                                conversation.status === 'active' ? 'success' :
                                conversation.status === 'archived' ? 'warning' : 'destructive'
                              }
                              className="text-xs"
                            >
                              {conversation.status}
                            </Badge>
                            <span className="text-xs text-neutral-400 dark:text-neutral-500">
                              {formatRelativeTime(conversation.updated_at)}
                            </span>
                          </div>
                        </div>
                        <DropdownMenu align="right">
                          <Button variant="ghost" size="sm" className="p-1 opacity-0 group-hover:opacity-100">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                          <DropdownMenuItem icon={<Edit2 className="h-4 w-4" />} onClick={() => {}}>
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            icon={
                              conversation.status === 'active'
                                ? <Archive className="h-4 w-4" />
                                : <MessageSquare className="h-4 w-4" />
                            }
                            onClick={() => handleStatusChange(
                              conversation,
                              conversation.status === 'active' ? 'archived' : 'active'
                            )}
                          >
                            {conversation.status === 'active' ? 'Archive' : 'Activate'}
                          </DropdownMenuItem>
                          <DropdownMenuItem icon={<Star className="h-4 w-4" />} onClick={() => {}}>Favorite</DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem icon={<Trash2 className="h-4 w-4" />} destructive onClick={() => handleDelete(conversation.id)}>
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
        </aside>

        <div className="flex-1">
          <Card className="h-[calc(100vh-180px)] flex flex-col">
            <CardHeader>
              <CardTitle>Welcome to AI Support</CardTitle>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                Select a conversation from the sidebar or create a new one to start chatting.
              </p>
            </CardHeader>
            <CardContent className="flex-1 flex items-center justify-center">
              <div className="text-center p-8">
                <Bot className="h-16 w-16 text-neutral-300 dark:text-neutral-700 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                  Ready to help
                </h2>
                <p className="text-neutral-500 dark:text-neutral-400 mb-6 max-w-md">
                  Start a new conversation to get assistance with customer support, document analysis,
                  or any other tasks you need help with.
                </p>
                <Button onClick={() => setIsCreating(true)} size="lg">
                  <Plus className="h-4 w-4 mr-2" />
                  Start New Conversation
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}