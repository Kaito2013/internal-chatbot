'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { apiClient, type TokenUsageResponse, type RAGEffectivenessResponse, type TopSourcesResponse } from '@/lib/api';
import { formatNumber, cn } from '@/lib/auth';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { Loader2, TrendingUp, Brain, FileText, Clock } from 'lucide-react';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

type Period = '7d' | '30d' | '90d';

export default function StatsPage() {
  const [period, setPeriod] = useState<Period>('7d');
  const [tokenUsage, setTokenUsage] = useState<TokenUsageResponse | null>(null);
  const [ragEffectiveness, setRagEffectiveness] = useState<RAGEffectivenessResponse | null>(null);
  const [topSources, setTopSources] = useState<TopSourcesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [tokenData, ragData, sourcesData] = await Promise.all([
          apiClient.getTokenUsage(period),
          apiClient.getRAGEffectiveness(period),
          apiClient.getTopSources(period, 10),
        ]);
        setTokenUsage(tokenData);
        setRagEffectiveness(ragData);
        setTopSources(sourcesData);
      } catch (err) {
        console.error('Failed to load stats:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [period]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  // Token usage chart data
  const tokenChartData = tokenUsage ? {
    labels: tokenUsage.data.map(d => 
      new Date(d.date).toLocaleDateString('vi', { month: 'short', day: 'numeric' })
    ),
    datasets: [
      {
        label: 'Input Tokens',
        data: tokenUsage.data.map(d => d.input_tokens),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.3,
      },
      {
        label: 'Output Tokens',
        data: tokenUsage.data.map(d => d.output_tokens),
        borderColor: 'rgb(16, 185, 129)',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.3,
      },
    ],
  } : null;

  // RAG effectiveness chart data
  const ragChartData = ragEffectiveness ? {
    labels: ragEffectiveness.data.map(d => 
      new Date(d.date).toLocaleDateString('vi', { month: 'short', day: 'numeric' })
    ),
    datasets: [
      {
        label: 'Total Requests',
        data: ragEffectiveness.data.map(d => d.total_requests),
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
        borderColor: 'rgb(59, 130, 246)',
        borderWidth: 1,
      },
      {
        label: 'RAG Requests',
        data: ragEffectiveness.data.map(d => d.rag_requests),
        backgroundColor: 'rgba(16, 185, 129, 0.5)',
        borderColor: 'rgb(16, 185, 129)',
        borderWidth: 1,
      },
    ],
  } : null;

  // Top sources chart (doughnut)
  const sourcesChartData = topSources && topSources.sources.length > 0 ? {
    labels: topSources.sources.map(s => s.filename),
    datasets: [
      {
        data: topSources.sources.map(s => s.reference_count),
        backgroundColor: [
          'rgba(59, 130, 246, 0.7)',
          'rgba(16, 185, 129, 0.7)',
          'rgba(245, 158, 11, 0.7)',
          'rgba(239, 68, 68, 0.7)',
          'rgba(139, 92, 246, 0.7)',
          'rgba(236, 72, 153, 0.7)',
          'rgba(20, 184, 166, 0.7)',
          'rgba(251, 146, 60, 0.7)',
          'rgba(99, 102, 241, 0.7)',
          'rgba(84, 172, 84, 0.7)',
        ],
        borderWidth: 0,
      },
    ],
  } : null;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Thống kê</h1>
          <p className="text-slate-500 mt-1">Biểu đồ và phân tích hiệu suất</p>
        </div>
        
        {/* Period Selector */}
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
          {(['7d', '30d', '90d'] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={cn(
                'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                period === p
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              )}
            >
              {p === '7d' ? '7 ngày' : p === '30d' ? '30 ngày' : '90 ngày'}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">
              Total Tokens
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-900">
              {formatNumber((tokenUsage?.total_input_tokens || 0) + (tokenUsage?.total_output_tokens || 0))}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {formatNumber(tokenUsage?.total_requests || 0)} requests
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">
              RAG Effectiveness
            </CardTitle>
            <Brain className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-900">
              {ragEffectiveness ? `${(ragEffectiveness.overall_effectiveness_rate * 100).toFixed(1)}%` : '0%'}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {formatNumber(ragEffectiveness?.total_rag_requests || 0)} RAG requests
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">
              Top Source
            </CardTitle>
            <FileText className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-900 truncate">
              {topSources?.sources[0]?.filename || 'N/A'}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {formatNumber(topSources?.sources[0]?.reference_count || 0)} references
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Token Usage Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Token Usage</CardTitle>
            <CardDescription>Input vs Output tokens theo thời gian</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              {tokenChartData ? (
                <Line data={tokenChartData} options={chartOptions} />
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">
                  No data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* RAG Effectiveness Chart */}
        <Card>
          <CardHeader>
            <CardTitle>RAG Effectiveness</CardTitle>
            <CardDescription>Total requests vs RAG requests</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              {ragChartData ? (
                <Bar data={ragChartData} options={chartOptions} />
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">
                  No data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Sources Doughnut */}
        <Card>
          <CardHeader>
            <CardTitle>Top Sources</CardTitle>
            <CardDescription>Most referenced documents</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {sourcesChartData ? (
                <Doughnut 
                  data={sourcesChartData} 
                  options={{
                    ...chartOptions,
                    scales: undefined,
                    plugins: {
                      ...chartOptions.plugins,
                      legend: {
                        position: 'right' as const,
                        labels: {
                          boxWidth: 12,
                          padding: 8,
                          font: { size: 11 },
                        },
                      },
                    },
                  }}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">
                  No data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Token Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>Token Breakdown</CardTitle>
            <CardDescription>Tỷ lệ Input/Output</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center">
              {tokenUsage && (tokenUsage.total_input_tokens + tokenUsage.total_output_tokens) > 0 ? (
                <div className="w-full space-y-4">
                  <div className="relative pt-1">
                    <div className="flex mb-2 items-center justify-between">
                      <div className="text-xs font-medium text-slate-600">Input</div>
                      <div className="text-xs text-slate-500">
                        {formatNumber(tokenUsage.total_input_tokens)}
                      </div>
                    </div>
                    <div className="overflow-hidden h-2 text-xs flex rounded bg-slate-100">
                      <div
                        style={{
                          width: `${(tokenUsage.total_input_tokens / (tokenUsage.total_input_tokens + tokenUsage.total_output_tokens)) * 100}%`,
                        }}
                        className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500"
                      />
                    </div>
                  </div>
                  <div className="relative pt-1">
                    <div className="flex mb-2 items-center justify-between">
                      <div className="text-xs font-medium text-slate-600">Output</div>
                      <div className="text-xs text-slate-500">
                        {formatNumber(tokenUsage.total_output_tokens)}
                      </div>
                    </div>
                    <div className="overflow-hidden h-2 text-xs flex rounded bg-slate-100">
                      <div
                        style={{
                          width: `${(tokenUsage.total_output_tokens / (tokenUsage.total_input_tokens + tokenUsage.total_output_tokens)) * 100}%`,
                        }}
                        className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-green-500"
                      />
                    </div>
                  </div>
                  
                  <div className="mt-6 pt-4 border-t">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Avg Input/msg</span>
                      <span className="font-medium">
                        {tokenUsage.total_requests > 0
                          ? Math.round(tokenUsage.total_input_tokens / tokenUsage.total_requests)
                          : 0}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm mt-2">
                      <span className="text-slate-500">Avg Output/msg</span>
                      <span className="font-medium">
                        {tokenUsage.total_requests > 0
                          ? Math.round(tokenUsage.total_output_tokens / tokenUsage.total_requests)
                          : 0}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-slate-400">No data</div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Top Sources List */}
        <Card>
          <CardHeader>
            <CardTitle>Sources List</CardTitle>
            <CardDescription>Reference counts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 overflow-auto">
              {topSources && topSources.sources.length > 0 ? (
                <div className="space-y-2">
                  {topSources.sources.map((source, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium text-primary">
                        {idx + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{source.filename}</p>
                        <p className="text-xs text-slate-400">{source.source.split('/').pop()}</p>
                      </div>
                      <span className="text-sm font-medium text-slate-600">
                        {formatNumber(source.reference_count)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">
                  No data
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
