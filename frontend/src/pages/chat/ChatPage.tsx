import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { formatRelativeTime, cn } from '@/utils/helpers';
import {
  Send,
  Paperclip,
  Mic,
  Bot,
  User,
  ChevronLeft,
  MoreVertical,
  Copy,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  Archive,
  Star,
  Trash2,
  Edit2,
  Download,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card';
import { Avatar } from '@/components/ui/Avatar';
import { DropdownMenu, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/Dropdown';
import { ScrollArea } from '@/components/ui/ScrollArea';
import { TypingIndicator } from '@/components/chat/TypingIndicator';
import { useAuth } from '@/context/AuthContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

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
  last_message?: Message;
}

interface Message {
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

interface ToolCall {
  id: string;
  type: 'function';
  function: { name: string; arguments: string };
}

interface ToolResult {
  tool_call_id: string;
  name: string;
  result?: unknown;
  error?: string;
}

interface ChatRequest {
  message: string;
  conversation_id?: string;
  use_rag?: boolean;
  knowledge_base_id?: string;
  use_tools?: boolean;
}

interface ChatResponse {
  conversation_id: string;
  message: string;
  message_id?: string;
}

async function fetchConversation(id: string): Promise<Conversation> {
  const response = await api.get(`/chat/conversations/${id}`);
  return response.data;
}

async function fetchMessages(conversationId: string): Promise<Message[]> {
  const response = await api.get(`/chat/conversations/${conversationId}/messages`);
  return response.data;
}

async function sendMessage(data: ChatRequest): Promise<ChatResponse> {
  const response = await api.post('/chat', data);
  return response.data;
}

async function streamMessage(data: ChatRequest, onChunk: (chunk: string) => void): Promise<void> {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('auth_tokens') ? JSON.parse(localStorage.getItem('auth_tokens')!).access_token : ''}`,
    },
    body: JSON.stringify(data),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) return;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data !== '[DONE]') {
          onChunk(data);
        }
      }
    }
  }
}

async function updateConversation(id: string, data: Partial<Conversation>): Promise<Conversation> {
  const response = await api.patch(`/chat/conversations/${id}`, data);
  return response.data;
}

async function deleteConversation(id: string): Promise<void> {
  await api.delete(`/chat/conversations/${id}`);
}

export function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [model, setModel] = useState('gpt-4-turbo-preview');
  const [temperature, setTemperature] = useState(0.7);
  const [useRag, setUseRag] = useState(true);
  const [useTools, setUseTools] = useState(true);
  const [knowledgeBaseId, setKnowledgeBaseId] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { data: conversationData, isLoading: convLoading } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => fetchConversation(conversationId!),
    enabled: !!conversationId,
  });

  const { data: messagesData, isLoading: msgLoading } = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => fetchMessages(conversationId!),
    enabled: !!conversationId,
  });

  useEffect(() => {
    if (conversationData) {
      setConversation(conversationData);
      setModel(conversationData.model);
      setTemperature(conversationData.temperature);
    }
  }, [conversationData]);

  useEffect(() => {
    if (messagesData) {
      setMessages(messagesData);
    }
  }, [messagesData]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, scrollToBottom]);

  const sendMutation = useMutation({
    mutationFn: sendMessage,
    onSuccess: (response) => {
      if (!conversationId) {
        navigate(`/chat/${response.conversation_id}`, { replace: true });
      }
      queryClient.invalidateQueries({ queryKey: ['messages', response.conversation_id] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: conversationId || '',
      role: 'user',
      content: input,
      tokens: 0,
      tool_calls: [],
      tool_results: [],
      metadata: {},
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsStreaming(true);
    setStreamingContent('');

    try {
      await streamMessage(
        {
          message: currentInput,
          conversation_id: conversationId,
          use_rag: useRag,
          knowledge_base_id: knowledgeBaseId || undefined,
          use_tools: useTools,
        },
        (chunk) => {
          setStreamingContent((prev) => prev + chunk);
        }
      );

      queryClient.invalidateQueries({ queryKey: ['messages', conversationId || ''] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsStreaming(false);
      setStreamingContent('');
    }
  };

  const handleRegenerate = async (messageId: string) => {
    const messageIndex = messages.findIndex((m) => m.id === messageId);
    if (messageIndex <= 0) return;

    const previousMessage = messages[messageIndex - 1];
    if (previousMessage.role !== 'user') return;

    const newMessages = messages.slice(0, messageIndex);
    setMessages(newMessages);
    setIsStreaming(true);
    setStreamingContent('');

    try {
      await streamMessage(
        {
          message: previousMessage.content,
          conversation_id: conversationId,
          use_rag: useRag,
          knowledge_base_id: knowledgeBaseId || undefined,
          use_tools: useTools,
        },
        (chunk) => {
          setStreamingContent((prev) => prev + chunk);
        }
      );

      queryClient.invalidateQueries({ queryKey: ['messages', conversationId || ''] });
    } catch (error) {
      console.error('Failed to regenerate:', error);
    } finally {
      setIsStreaming(false);
      setStreamingContent('');
    }
  };

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  const handleDeleteConversation = async () => {
    if (!conversationId || !confirm('Are you sure you want to delete this conversation?')) return;
    await deleteConversation(conversationId);
    navigate('/chat');
  };

  if (!conversationId && messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center p-8">
          <Bot className="h-16 w-16 text-neutral-300 dark:text-neutral-700 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">Start a new conversation</h2>
          <p className="text-neutral-500 dark:text-neutral-400 mb-6">Select a conversation from the sidebar or create a new one</p>
          <Button onClick={() => navigate('/chat')}>New Chat</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] -m-6">
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-neutral-200 dark:border-neutral-800 px-4 py-3 shrink-0">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <Button variant="ghost" size="sm" onClick={() => navigate('/chat')} className="lg:hidden">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="min-w-0">
              <h1 className="font-medium text-neutral-900 dark:text-neutral-100 truncate">
                {conversation?.title || 'New Conversation'}
              </h1>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                {conversation?.status === 'active' ? 'Active' : conversation?.status}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
<DropdownMenu align="right">
                <Button variant="ghost" size="sm" className="p-2" aria-label="Conversation options">
                  <MoreVertical className="h-5 w-5" />
                </Button>
                <DropdownMenuItem icon={<Edit2 className="h-4 w-4" />} onClick={() => setShowSettings(true)}>
                  Settings
                </DropdownMenuItem>
                <DropdownMenuItem icon={<Archive className="h-4 w-4" />} onClick={() => {}}>
                  Archive
                </DropdownMenuItem>
                <DropdownMenuItem icon={<Star className="h-4 w-4" />} onClick={() => {}}>
                  Favorite
                </DropdownMenuItem>
                <DropdownMenuItem icon={<Download className="h-4 w-4" />} onClick={() => {}}>
                  Export
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem icon={<Trash2 className="h-4 w-4" />} destructive onClick={handleDeleteConversation}>
                  Delete
                </DropdownMenuItem>
              </DropdownMenu>
          </div>
        </div>

        <ScrollArea className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              isStreaming={isStreaming && message.id === messages[messages.length - 1]?.id}
              streamingContent={streamingContent}
              onRegenerate={handleRegenerate}
              onCopy={handleCopy}
            />
          ))}
          {isStreaming && (
            <MessageBubble
              message={{
                id: 'streaming',
                conversation_id: conversationId || '',
                role: 'assistant',
                content: '',
                tokens: 0,
                tool_calls: [],
                tool_results: [],
                metadata: {},
                created_at: new Date().toISOString(),
              }}
              isStreaming={true}
              streamingContent={streamingContent}
              onRegenerate={() => {}}
              onCopy={() => {}}
            />
          )}
          {isStreaming && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </ScrollArea>

        <div className="border-t border-neutral-200 dark:border-neutral-800 p-4">
          <form onSubmit={handleSend} className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message AI Support..."
                className="w-full min-h-[44px] max-h-48 px-4 py-3 pr-12 text-sm bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                rows={1}
                disabled={isStreaming}
              />
              <div className="absolute bottom-2 right-2 flex items-center gap-1">
                <Button variant="ghost" size="sm" className="p-1.5" disabled={isStreaming} aria-label="Attach file">
                  <Paperclip className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" className="p-1.5" disabled={isStreaming} aria-label="Voice input">
                  <Mic className="h-4 w-4" />
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  className="p-1.5"
                  disabled={!input.trim() || isStreaming}
                  aria-label="Send message"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </form>
          <div className="flex items-center justify-between mt-2 text-xs text-neutral-500 dark:text-neutral-400">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useRag}
                  onChange={(e) => setUseRag(e.target.checked)}
                  className="rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                />
                RAG
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useTools}
                  onChange={(e) => setUseTools(e.target.checked)}
                  className="rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                />
                Tools
              </label>
            </div>
            <span>{model} · Temp: {temperature}</span>
          </div>
        </div>
      </div>

      {showSettings && (
        <ConversationSettings
          conversation={conversation}
          model={model}
          temperature={temperature}
          onModelChange={setModel}
          onTemperatureChange={setTemperature}
          onClose={() => setShowSettings(false)}
          onSave={() => {
            if (conversationId) {
              updateConversation(conversationId, { model, temperature });
              setShowSettings(false);
            }
          }}
        />
      )}
    </div>
  );
}

function MessageBubble({
  message,
  isStreaming,
  streamingContent,
  onRegenerate,
  onCopy,
}: {
  message: Message;
  isStreaming?: boolean;
  streamingContent?: string;
  onRegenerate: (id: string) => void;
  onCopy: (content: string) => void;
}) {
  const content = isStreaming ? streamingContent : message.content;
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <Avatar
        name={isUser ? 'You' : 'AI'}
        size="sm"
        className={cn('flex-shrink-0 mt-1', isUser && 'ml-2', !isUser && 'mr-2')}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </Avatar>
      <div className={cn('flex-1 max-w-[85%]', isUser && 'text-right')}>
        <div
          className={cn(
            'inline-block px-4 py-2 rounded-2xl text-sm whitespace-pre-wrap',
            isUser
              ? 'bg-primary-600 text-white rounded-tr-sm'
              : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 rounded-tl-sm'
          )}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw]}
            components={{
              code: ({ children, ...props }) => (
                <pre className="p-3 rounded-lg bg-neutral-900 dark:bg-neutral-950 overflow-x-auto text-sm">
                  <code {...props}>{children}</code>
                </pre>
              ),
            }}
          >
            {content || ' '}
          </ReactMarkdown>
        </div>

        {(message.tool_calls.length > 0 || message.tool_results.length > 0) && (
          <div className="mt-2 space-y-1">
            {message.tool_calls.map((tc) => (
              <div key={tc.id} className="text-xs text-neutral-500 dark:text-neutral-400 font-mono px-2">
                🔧 {tc.function.name}({tc.function.arguments})
              </div>
            ))}
            {message.tool_results.map((tr) => (
              <div key={tr.tool_call_id} className="text-xs text-green-600 dark:text-green-400 font-mono px-2">
                ✓ {tr.name}: {JSON.stringify(tr.result).slice(0, 100)}...
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs text-neutral-400 dark:text-neutral-500">
            {formatRelativeTime(message.created_at)}
          </span>
          {!isUser && !isStreaming && (
            <>
              <Button variant="ghost" size="sm" className="p-1" onClick={() => onCopy(message.content)} aria-label="Copy">
                <Copy className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" className="p-1" onClick={() => onRegenerate(message.id)} aria-label="Regenerate">
                <RotateCcw className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" className="p-1" aria-label="Good response">
                <ThumbsUp className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" className="p-1" aria-label="Bad response">
                <ThumbsDown className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ConversationSettings({
  conversation,
  model,
  temperature,
  onModelChange,
  onTemperatureChange,
  onClose,
  onSave,
}: {
  conversation: Conversation | null;
  model: string;
  temperature: number;
  onModelChange: (model: string) => void;
  onTemperatureChange: (temp: number) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Conversation Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="label">Model</label>
            <select
              value={model}
              onChange={(e) => onModelChange(e.target.value)}
              className="input"
            >
              <option value="gpt-4-turbo-preview">GPT-4 Turbo</option>
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
            </select>
          </div>
          <div>
            <label className="label">Temperature: {temperature.toFixed(1)}</label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => onTemperatureChange(parseFloat(e.target.value))}
              className="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none accent-primary-600"
            />
          </div>
          {conversation?.system_prompt && (
            <div>
              <label className="label">System Prompt</label>
              <textarea
                defaultValue={conversation.system_prompt}
                className="input min-h-[100px] resize-y"
                readOnly
              />
            </div>
          )}
        </CardContent>
        <CardFooter className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={onSave}>Save</Button>
        </CardFooter>
      </Card>
    </div>
  );
}