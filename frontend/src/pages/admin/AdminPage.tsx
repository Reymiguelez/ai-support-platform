import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { formatRelativeTime, formatNumber, cn } from '@/utils/helpers';
import {
  Users,
  MessageSquare,
  FileText,
  Database,
  TrendingUp,
  Bot,
  Clock,
  CheckCircle,
  AlertCircle,
  BarChart3,
  Cpu,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';

interface DashboardStats {
  users: { total: number; customers: number; agents: number; admins: number; new_this_week: number };
  conversations: { total: number; active: number; total_messages: number; avg_messages_per_conversation: number; new_this_week: number };
  documents: { total: number; processed: number; processing_rate: number };
  knowledge_bases: { total: number; active: number };
  tools: { total: number; active: number; total_executions: number; success_rate: number };
}

interface ActivityChartData {
  users: { date: string; count: number }[];
  conversations: { date: string; count: number }[];
  messages: { date: string; count: number }[];
}

interface AIUsageData {
  models: { model: string; requests: number; total_tokens: number; avg_response_time_ms: number }[];
  tools: { name: string; category: string; executions: number; avg_execution_time_ms: number }[];
}

interface SystemConfig {
  environment: string;
  version: string;
  api_prefix: string;
  openai_model: string;
  embedding_model: string;
  rate_limit: string;
  vector_search: { top_k: number; similarity_threshold: number };
  conversation_memory_window: number;
  allowed_file_types: string[];
  max_file_size_mb: number;
}

async function fetchAdminStats(): Promise<DashboardStats> {
  const response = await api.get('/admin/dashboard/stats');
  return response.data;
}

async function fetchActivity(): Promise<ActivityChartData> {
  const response = await api.get('/admin/dashboard/activity', { params: { days: 30 } });
  return response.data;
}

async function fetchAIUsage(): Promise<AIUsageData> {
  const response = await api.get('/admin/dashboard/ai-usage', { params: { days: 30 } });
  return response.data;
}

async function fetchSystemConfig(): Promise<SystemConfig> {
  const response = await api.get('/admin/system/config');
  return response.data;
}

const overviewStats = [
  { name: 'Total Users', key: 'users.total', icon: Users, color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400', subKey: 'users.new_this_week', subLabel: 'new this week' },
  { name: 'Conversations', key: 'conversations.total', icon: MessageSquare, color: 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400', subKey: 'conversations.active', subLabel: 'active' },
  { name: 'Documents', key: 'documents.total', icon: FileText, color: 'text-purple-600 bg-purple-100 dark:bg-purple-900/30 dark:text-purple-400', subKey: 'documents.processed', subLabel: 'processed' },
  { name: 'Knowledge Bases', key: 'knowledge_bases.total', icon: Database, color: 'text-orange-600 bg-orange-100 dark:bg-orange-900/30 dark:text-orange-400', subKey: 'knowledge_bases.active', subLabel: 'active' },
];

function getNestedValue(obj: unknown, path: string): number {
  return path.split('.').reduce((o: unknown, k) => (o as Record<string, unknown>)[k], obj) as number;
}

function StatCard({ name, value, icon: Icon, color, subValue, subLabel }: {
  name: string; value: number; icon: React.ComponentType<{ className?: string }>;
  color: string; subValue?: number; subLabel?: string;
}) {
  return (
    <Card className="card-hover">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{name}</p>
            <p className="mt-1 text-3xl font-bold text-neutral-900 dark:text-neutral-100">{formatNumber(value)}</p>
            {subValue !== undefined && subLabel && (
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{formatNumber(subValue)} {subLabel}</p>
            )}
          </div>
          <div className={cn('p-3 rounded-xl', color)}><Icon className="h-6 w-6" /></div>
        </div>
      </CardContent>
    </Card>
  );
}

function AIUsagePage({ stats, aiUsage }: { stats?: DashboardStats; aiUsage?: AIUsageData }) {
  const totalRequests = aiUsage?.models.reduce((a, b) => a + b.requests, 0) || 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard name="Total Tools" value={stats?.tools.total || 0} icon={Zap} color="text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400" subValue={stats?.tools.active} subLabel="active" />
        <StatCard name="Tool Executions" value={stats?.tools.total_executions || 0} icon={Cpu} color="text-purple-600 bg-purple-100 dark:bg-purple-900/30 dark:text-purple-400" subValue={stats?.tools.success_rate} subLabel="% success" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Bot className="h-5 w-5 text-primary-600" /> Model Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {aiUsage?.models.map((model) => {
              const percentage = model.requests > 0 && totalRequests > 0 ? Math.min(100, (model.requests / totalRequests) * 100) : 0;
              return (
                <div key={model.model}>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-neutral-700 dark:text-neutral-300">{model.model}</span>
                    <span className="text-neutral-500 dark:text-neutral-400">{formatNumber(model.requests)} requests · {formatNumber(model.total_tokens)} tokens</span>
                  </div>
                  <div className="h-2 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden">
                    <div className="h-full bg-primary-600 rounded-full" style={{ width: `${percentage}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Zap className="h-5 w-5 text-primary-600" /> Tool Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  <th className="pb-3 px-4">Tool</th>
                  <th className="pb-3 px-4">Category</th>
                  <th className="pb-3 px-4">Executions</th>
                  <th className="pb-3 px-4">Avg Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                {aiUsage?.tools.map((tool) => (
                  <tr key={tool.name}>
                    <td className="py-3 px-4 text-sm font-medium text-neutral-900 dark:text-neutral-100">{tool.name}</td>
                    <td className="py-3 px-4 text-sm text-neutral-500 dark:text-neutral-400"><Badge variant="neutral">{tool.category}</Badge></td>
                    <td className="py-3 px-4 text-sm text-neutral-700 dark:text-neutral-300">{formatNumber(tool.executions)}</td>
                    <td className="py-3 px-4 text-sm text-neutral-500 dark:text-neutral-400">{tool.avg_execution_time_ms.toFixed(0)}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SystemConfigPage({ config }: { config?: SystemConfig }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>System Configuration</CardTitle>
          <CardDescription>Current system settings and environment info</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 md:grid-cols-2">
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Environment</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.environment}</dd></div>
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Version</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.version}</dd></div>
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">API Prefix</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.api_prefix}</dd></div>
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">OpenAI Model</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.openai_model}</dd></div>
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Embedding Model</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.embedding_model}</dd></div>
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Rate Limit</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.rate_limit}</dd></div>
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Vector Search Top K</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.vector_search.top_k}</dd></div>
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Similarity Threshold</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.vector_search.similarity_threshold}</dd></div>
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Conversation Memory</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.conversation_memory_window} messages</dd></div>
            <div><dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Max File Size</dt><dd className="mt-1 text-lg font-mono text-neutral-900 dark:text-neutral-100">{config?.max_file_size_mb}MB</dd></div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Allowed File Types</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {config?.allowed_file_types.map((type, i) => (
              <Badge key={i} variant="neutral">{type}</Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function AdminPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({ queryKey: ['admin-stats'], queryFn: fetchAdminStats, refetchInterval: 60000 });
  const { data: activity } = useQuery({ queryKey: ['admin-activity'], queryFn: fetchActivity });
  const { data: aiUsage } = useQuery({ queryKey: ['admin-ai-usage'], queryFn: fetchAIUsage });
  const { data: config } = useQuery({ queryKey: ['admin-config'], queryFn: fetchSystemConfig });

  if (statsLoading) {
    return <div className="space-y-6 animate-pulse"><div className="grid gap-4 md:grid-cols-4">{[...Array(4)].map((_, i) => <Card key={i} className="h-32" />)}</div></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Admin Dashboard</h1>
          <p className="text-neutral-500 dark:text-neutral-400">System overview and analytics</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {overviewStats.map((stat) => (
          <StatCard key={stat.name} name={stat.name} value={getNestedValue(stats, stat.key)} icon={stat.icon} color={stat.color} subValue={getNestedValue(stats, stat.subKey)} subLabel={stat.subLabel} />
        ))}
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="ai-usage">AI Usage</TabsTrigger>
          <TabsTrigger value="system">System Config</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5 text-primary-600" /> Recent Activity</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                    <div className="flex items-center gap-3"><div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30"><Users className="h-5 w-5 text-blue-600" /></div><div><p className="text-sm font-medium">New Users</p><p className="text-xs text-neutral-500">{formatNumber(stats?.users.new_this_week || 0)} this week</p></div></div>
                    <Badge variant="primary">+{formatNumber(stats?.users.new_this_week || 0)}%</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                    <div className="flex items-center gap-3"><div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30"><MessageSquare className="h-5 w-5 text-green-600" /></div><div><p className="text-sm font-medium">New Conversations</p><p className="text-xs text-neutral-500">{formatNumber(stats?.conversations.new_this_week || 0)} this week</p></div></div>
                    <Badge variant="success">+{formatNumber(stats?.conversations.new_this_week || 0)}%</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Users className="h-5 w-5 text-primary-600" /> User Breakdown</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { label: 'Customers', value: stats?.users.customers || 0, color: 'bg-blue-100 dark:bg-blue-900/30', iconColor: 'text-blue-600', icon: Users },
                    { label: 'Support Agents', value: stats?.users.agents || 0, color: 'bg-green-100 dark:bg-green-900/30', iconColor: 'text-green-600', icon: Bot },
                    { label: 'Administrators', value: stats?.users.admins || 0, color: 'bg-purple-100 dark:bg-purple-900/30', iconColor: 'text-purple-600', icon: CheckCircle },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between">
                      <div className="flex items-center gap-3"><div className={cn('p-2 rounded-lg', item.color)}><item.icon className={cn('h-5 w-5', item.iconColor)} /></div><span className="text-sm font-medium">{item.label}</span></div>
                      <Badge variant="primary">{formatNumber(item.value)}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        <TabsContent value="ai-usage"><AIUsagePage stats={stats} aiUsage={aiUsage} /></TabsContent>
        <TabsContent value="system"><SystemConfigPage config={config} /></TabsContent>
      </Tabs>
    </div>
  );
}