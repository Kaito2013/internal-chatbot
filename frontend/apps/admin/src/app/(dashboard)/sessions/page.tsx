'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiClient, type Session, type SessionDetail, type ChatLog } from '@/lib/api';
import { formatDate, formatRelativeTime, getErrorMessage, cn } from '@/lib/auth';
import { 
  Search, RefreshCw, Trash2, Download, ChevronLeft, ChevronRight,
  Loader2, MessageSquare, X, User, Bot, ExternalLink
} from 'lucide-react';
import { toast, Toaster } from 'sonner';

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedSession, setSelectedSession] = useState<SessionDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.getSessions({ page, page_size: pageSize });
      setSessions(response.sessions);
      setTotal(response.total);
      setTotalPages(Math.ceil(response.total / pageSize));
    } catch (err) {
      toast.error('Failed to load sessions');
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize]);

  const searchSessions = useCallback(async (query: string) => {
    if (!query.trim()) {
      fetchSessions();
      return;
    }
    
    setIsSearching(true);
    try {
      const response = await apiClient.searchSessions(query);
      setSessions(response.sessions);
      setTotal(response.total);
      setTotalPages(1);
    } catch (err) {
      toast.error('Search failed');
    } finally {
      setIsSearching(false);
    }
  }, [fetchSessions]);

  useEffect(() => {
    if (searchQuery) {
      const timer = setTimeout(() => {
        searchSessions(searchQuery);
      }, 300);
      return () => clearTimeout(timer);
    } else {
      fetchSessions();
    }
  }, [searchQuery, fetchSessions, searchSessions]);

  const viewSessionDetail = async (sessionId: string) => {
    setIsLoadingDetail(true);
    try {
      const detail = await apiClient.getSessionDetail(sessionId);
      setSelectedSession(detail);
    } catch (err) {
      toast.error('Failed to load session details');
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleDelete = async (sessionId: string) => {
    if (!confirm('Delete this session and all its messages?')) return;
    
    setDeletingId(sessionId);
    try {
      await apiClient.deleteSession(sessionId);
      toast.success('Session deleted');
      fetchSessions();
    } catch (err) {
      toast.error(`Failed to delete: ${getErrorMessage(err)}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleExport = async (sessionId: string, format: 'json' | 'csv') => {
    try {
      const blob = await apiClient.exportSession(sessionId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `session_${sessionId}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Export started');
    } catch (err) {
      toast.error('Export failed');
    }
  };

  const parseSources = (sourcesJson: string | null): any[] => {
    if (!sourcesJson) return [];
    try {
      return JSON.parse(sourcesJson);
    } catch {
      return [];
    }
  };

  return (
    <div className="space-y-6">
      <Toaster position="top-right" />
      
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Phiên hội thoại</h1>
        <p className="text-slate-500 mt-1">Xem và quản lý lịch sử chat</p>
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2"
            >
              <X className="h-4 w-4 text-slate-400" />
            </button>
          )}
        </div>
        <Button variant="outline" onClick={fetchSessions}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Sessions List */}
      <Card>
        <CardHeader>
          <CardTitle>Danh sách phiên</CardTitle>
          <CardDescription>
            {searchQuery 
              ? `${total} kết quả tìm kiếm cho "${searchQuery}"`
              : `${total} phiên | Trang ${page}/${totalPages}`
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading || isSearching ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No sessions found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className="flex items-center gap-4 p-4 border rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <MessageSquare className="h-5 w-5 text-primary" />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-slate-900 font-mono text-sm">{session.id}</p>
                      <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-500 rounded">
                        {session.message_count} msgs
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                      {session.username && (
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {session.username}
                        </span>
                      )}
                      <span>Updated {formatRelativeTime(session.updated_at)}</span>
                      <span>{formatDate(session.created_at)}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => viewSessionDetail(session.id)}
                    >
                      View
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport(session.id, 'json')}
                      title="Export JSON"
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(session.id)}
                      disabled={deletingId === session.id}
                      className="text-destructive hover:text-destructive hover:border-destructive"
                    >
                      {deletingId === session.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {!searchQuery && totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <span className="text-sm text-slate-500">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Session Detail Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            <CardHeader className="flex-shrink-0">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Session Detail</CardTitle>
                  <CardDescription className="font-mono">{selectedSession.id}</CardDescription>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedSession(null)}
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              {isLoadingDetail ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Session Info */}
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div className="p-3 bg-slate-50 rounded-lg">
                      <p className="text-slate-500">User</p>
                      <p className="font-medium">{selectedSession.username || 'Anonymous'}</p>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-lg">
                      <p className="text-slate-500">Messages</p>
                      <p className="font-medium">{selectedSession.message_count}</p>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-lg">
                      <p className="text-slate-500">Created</p>
                      <p className="font-medium">{formatDate(selectedSession.created_at)}</p>
                    </div>
                  </div>

                  {/* Messages */}
                  <div className="space-y-4">
                    <h3 className="font-medium text-slate-900">Messages</h3>
                    {selectedSession.messages.map((msg, idx) => (
                      <div key={idx} className="space-y-2">
                        {/* User Message */}
                        <div className="flex gap-3">
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                            <User className="h-4 w-4 text-blue-600" />
                          </div>
                          <div className="flex-1">
                            <p className="font-medium text-sm text-slate-900">User</p>
                            <div className="mt-1 p-3 bg-slate-50 rounded-lg text-sm">
                              {msg.question}
                            </div>
                          </div>
                        </div>

                        {/* Assistant Response */}
                        <div className="flex gap-3">
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <Bot className="h-4 w-4 text-primary" />
                          </div>
                          <div className="flex-1">
                            <p className="font-medium text-sm text-slate-900">
                              Assistant ({msg.model_used})
                            </p>
                            <div className="mt-1 p-3 bg-primary/5 rounded-lg text-sm">
                              {msg.answer}
                            </div>
                            
                            {/* Sources */}
                            {msg.sources_json && parseSources(msg.sources_json).length > 0 && (
                              <div className="mt-2">
                                <p className="text-xs text-slate-500 mb-1">Sources:</p>
                                <div className="flex flex-wrap gap-1">
                                  {parseSources(msg.sources_json).map((source, sIdx) => (
                                    <span
                                      key={sIdx}
                                      className="px-2 py-0.5 text-xs bg-slate-100 rounded truncate max-w-[200px]"
                                      title={source.source}
                                    >
                                      {source.source.split('/').pop()}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Metadata */}
                            <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
                              <span>In: {msg.tokens_input} tokens</span>
                              <span>Out: {msg.tokens_output} tokens</span>
                              <span>{msg.latency_ms}ms</span>
                              <span>{msg.mode}</span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="border-t my-4" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
