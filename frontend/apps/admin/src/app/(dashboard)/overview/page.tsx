'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { apiClient, type OverviewStats, type TokenUsageResponse } from '@/lib/api';
import { formatNumber, formatDate } from '@/lib/auth';
import { 
  MessageSquare, Users, FileText, Brain, 
  Clock, TrendingUp, Zap, Activity
} from 'lucide-react';

export default function OverviewPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [tokenUsage, setTokenUsage] = useState<TokenUsageResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, tokenData] = await Promise.all([
          apiClient.getOverviewStats(30),
          apiClient.getTokenUsage('7d'),
        ]);
        setStats(statsData);
        setTokenUsage(tokenData);
      } catch (err) {
        setError('Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-900">Tổng quan</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 bg-slate-200 rounded w-24" />
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-slate-200 rounded w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="p-6">
        <div className="bg-destructive/10 text-destructive p-4 rounded-lg">
          {error || 'Failed to load data'}
        </div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Tổng phiên',
      value: formatNumber(stats.total_sessions),
      description: '30 ngày gần đây',
      icon: MessageSquare,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Tin nhắn',
      value: formatNumber(stats.total_messages),
      description: '30 ngày gần đây',
      icon: Activity,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Người dùng',
      value: formatNumber(stats.total_users),
      description: 'Người dùng duy nhất',
      icon: Users,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      title: 'Tài liệu',
      value: formatNumber(stats.total_documents),
      description: `${formatNumber(stats.total_chunks)} chunks`,
      icon: FileText,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
  ];

  const performanceCards = [
    {
      title: 'Trung bình Latency',
      value: `${stats.avg_latency_ms.toFixed(0)}ms`,
      description: 'Thời gian phản hồi TB',
      icon: Clock,
      color: 'text-cyan-600',
      bgColor: 'bg-cyan-50',
    },
    {
      title: 'Input Tokens',
      value: formatNumber(stats.token_stats.total_input_tokens),
      description: `TB: ${stats.token_stats.avg_input_tokens.toFixed(0)}/msg`,
      icon: TrendingUp,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
    },
    {
      title: 'Output Tokens',
      value: formatNumber(stats.token_stats.total_output_tokens),
      description: `TB: ${stats.token_stats.avg_output_tokens.toFixed(0)}/msg`,
      icon: Zap,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
    },
    {
      title: 'RAG Requests',
      value: tokenUsage?.data.reduce((sum, d) => sum + d.request_count, 0) || 0,
      description: '7 ngày gần đây',
      icon: Brain,
      color: 'text-rose-600',
      bgColor: 'bg-rose-50',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Tổng quan</h1>
        <p className="text-slate-500 mt-1">Thống kê tổng quan về hoạt động chatbot</p>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-slate-600">
                {card.title}
              </CardTitle>
              <div className={`p-2 rounded-lg ${card.bgColor}`}>
                <card.icon className={`h-4 w-4 ${card.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-900">{card.value}</div>
              <p className="text-xs text-slate-500 mt-1">{card.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Performance Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {performanceCards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-slate-600">
                {card.title}
              </CardTitle>
              <div className={`p-2 rounded-lg ${card.bgColor}`}>
                <card.icon className={`h-4 w-4 ${card.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-900">{card.value}</div>
              <p className="text-xs text-slate-500 mt-1">{card.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Token Usage Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Token Usage (7 ngày)</CardTitle>
            <CardDescription>
              Tổng input/output tokens theo ngày
            </CardDescription>
          </CardHeader>
          <CardContent>
            {tokenUsage && tokenUsage.data.length > 0 ? (
              <div className="space-y-4">
                {/* Simple bar chart representation */}
                <div className="flex items-end gap-2 h-40">
                  {tokenUsage.data.map((day, idx) => {
                    const maxTokens = Math.max(...tokenUsage.data.map(d => d.total_tokens));
                    const height = maxTokens > 0 ? (day.total_tokens / maxTokens) * 100 : 0;
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                        <div 
                          className="w-full bg-primary/20 rounded-t relative"
                          style={{ height: `${height}%`, minHeight: '4px' }}
                        >
                          <div 
                            className="absolute bottom-0 w-full bg-primary rounded-t"
                            style={{ height: `${Math.max((day.output_tokens / day.total_tokens) * 100 || 0, 5)}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-500">
                          {new Date(day.date).toLocaleDateString('vi', { weekday: 'short' })}
                        </span>
                      </div>
                    );
                  })}
                </div>
                <div className="flex justify-center gap-4 text-xs">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded bg-primary/30" />
                    <span>Input</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded bg-primary" />
                    <span>Output</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-40 flex items-center justify-center text-slate-400">
                Chưa có dữ liệu token
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Token Stats</CardTitle>
            <CardDescription>
              Thống kê token tổng quan
            </CardDescription>
          </CardHeader>
          <CardContent>
            {tokenUsage && (
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                  <span className="text-sm text-slate-600">Tổng Input Tokens</span>
                  <span className="font-semibold">{formatNumber(tokenUsage.total_input_tokens)}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                  <span className="text-sm text-slate-600">Tổng Output Tokens</span>
                  <span className="font-semibold">{formatNumber(tokenUsage.total_output_tokens)}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                  <span className="text-sm text-slate-600">Tổng Requests</span>
                  <span className="font-semibold">{formatNumber(tokenUsage.total_requests)}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-primary/5 rounded-lg border border-primary/10">
                  <span className="text-sm font-medium">Tổng Tokens</span>
                  <span className="font-bold text-primary">
                    {formatNumber(tokenUsage.total_input_tokens + tokenUsage.total_output_tokens)}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
