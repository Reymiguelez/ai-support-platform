import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatNumber, cn } from '@/utils/helpers';
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
} from 'lucide-react';

interface DashboardStats {
  conversations: {
    total: number;
    active: number;
    total_messages: number;
    avg_messages_per_conversation: number;
  };
  documents: {
    total: number;
    processed: number;
    processing_rate: number;
  };
  tools: {
    total_executions: number;
    success_rate: number;
  };
}

async function fetchDashboardStats(): Promise<DashboardStats> {
  const response = await api.get('/dashboard/stats');
  return response.data;
}

const statCards = [
  {
    name: 'Total Conversations',
    key: 'conversations.total',
    icon: MessageSquare,
    color: 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400',
    subKey: 'conversations.active',
    subLabel: 'active',
  },
  {
    name: 'Documents',
    key: 'documents.total',
    icon: FileText,
    color: 'text-purple-600 bg-purple-100 dark:bg-purple-900/30 dark:text-purple-400',
    subKey: 'documents.processed',
    subLabel: 'processed',
  },
  {
    name: 'Tool Executions',
    key: 'tools.total_executions',
    icon: Bot,
    color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400',
    subKey: 'tools.success_rate',
    subLabel: 'success rate',
  },
];

function getNestedValue(obj: unknown, path: string): number {
  return path.split('.').reduce((o: unknown, k) => (o as Record<string, unknown>)[k], obj) as number;
}

function StatCard({
  name,
  value,
  icon: Icon,
  color,
  subValue,
  subLabel,
  trend,
}: {
  name: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  subValue?: number;
  subLabel?: string;
  trend?: number;
}) {
  return (
    <Card className="card-hover">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{name}</p>
            <p className="mt-1 text-3xl font-bold text-neutral-900 dark:text-neutral-100">{formatNumber(value)}</p>
            {subValue !== undefined && subLabel && (
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                {formatNumber(subValue)} {subLabel}
              </p>
            )}
          </div>
          <div className={cn('p-3 rounded-xl', color)}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
        {trend !== undefined && (
          <div className="mt-4 flex items-center gap-1">
            <span className={cn('text-sm font-medium', trend >= 0 ? 'text-green-600' : 'text-red-600')}>
              {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
            </span>
            <span className="text-sm text-neutral-500 dark:text-neutral-400">vs last period</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: fetchDashboardStats,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Dashboard</h1>
          <div className="h-10 w-40 bg-neutral-200 dark:bg-neutral-800 rounded-lg" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-lg font-medium text-neutral-900 dark:text-neutral-100">Failed to load dashboard</h2>
        <p className="text-neutral-500 dark:text-neutral-400 mt-2">{error instanceof Error ? error.message : 'Unknown error'}</p>
        <Button onClick={() => refetch()} className="mt-4" variant="primary">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Dashboard</h1>
          <p className="text-neutral-500 dark:text-neutral-400">Overview of your AI Support Platform</p>
        </div>
        <Button variant="outline" onClick={() => refetch()} size="sm">
          <svg className="h-4 w-4 mr-2 animate-spin" viewBox="0 0 24 24"><path d="M23 4v6h-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><path d="M1 20v-6h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <StatCard
            key={stat.name}
            name={stat.name}
            value={getNestedValue(stats, stat.key)}
            icon={stat.icon}
            color={stat.color}
            subValue={getNestedValue(stats, stat.subKey)}
            subLabel={stat.subLabel}
          />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary-600" />
              AI Usage
            </CardTitle>
            <CardDescription>Model and tool usage statistics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-medium text-neutral-700 dark:text-neutral-300">GPT-4 Turbo</span>
                  <span className="text-neutral-500 dark:text-neutral-400">{formatNumber(stats?.conversations.total_messages || 0)} messages</span>
                </div>
                <div className="h-2 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden">
                  <div className="h-full bg-primary-600 rounded-full" style={{ width: '75%' }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-medium text-neutral-700 dark:text-neutral-300">GPT-3.5 Turbo</span>
                  <span className="text-neutral-500 dark:text-neutral-400">{formatNumber(Math.floor((stats?.conversations.total_messages || 0) * 0.25))} messages</span>
                </div>
                <div className="h-2 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden">
                  <div className="h-full bg-green-600 rounded-full" style={{ width: '25%' }} />
                </div>
              </div>
              <div className="pt-4 border-t border-neutral-200 dark:border-neutral-800">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-neutral-700 dark:text-neutral-300">Tool Success Rate</span>
                  <Badge variant="success">{stats?.tools.success_rate?.toFixed(1) || 0}%</Badge>
                </div>
                <div className="h-2 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden mt-2">
                  <div className="h-full bg-green-600 rounded-full" style={{ width: `${stats?.tools.success_rate || 0}%` }} />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary-600" />
              Recent Activity
            </CardTitle>
            <CardDescription>Platform activity over the last 30 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">New user registered</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">2 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                  <MessageSquare className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">New conversation started</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
                  <FileText className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Document processed</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">12 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800">
                <div className="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30">
                  <Database className="h-5 w-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Knowledge base updated</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">1 hour ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}