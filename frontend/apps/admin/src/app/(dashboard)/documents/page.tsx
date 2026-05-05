'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiClient, type Document, type DocumentListResponse } from '@/lib/api';
import { formatBytes, formatDate, getErrorMessage, cn } from '@/lib/auth';
import { 
  Upload, FileText, Trash2, RefreshCw, Search, 
  File, FileSpreadsheet, FileType, X, ChevronLeft, ChevronRight,
  Loader2
} from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { toast, Toaster } from 'sonner';

const fileTypeIcons: Record<string, React.ReactNode> = {
  txt: <File className="h-5 w-5 text-blue-500" />,
  md: <FileText className="h-5 w-5 text-blue-500" />,
  pdf: <FileSpreadsheet className="h-5 w-5 text-red-500" />,
  docx: <FileSpreadsheet className="h-5 w-5 text-purple-500" />,
  html: <FileType className="h-5 w-5 text-orange-500" />,
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [reingestingId, setReingestingId] = useState<string | null>(null);
  const [error, setError] = useState('');

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await apiClient.getDocuments({ page, page_size: pageSize });
      setDocuments(response.documents);
      setTotal(response.total);
      setTotalPages(response.total_pages);
    } catch (err) {
      setError('Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      setIsUploading(true);
      try {
        await apiClient.uploadDocument(file);
        toast.success(`Uploaded: ${file.name}`);
        fetchDocuments();
      } catch (err) {
        toast.error(`Failed to upload ${file.name}: ${getErrorMessage(err)}`);
      }
    }
    setIsUploading(false);
  }, [fetchDocuments]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/html': ['.html'],
    },
    disabled: isUploading,
  });

  const handleDelete = async (doc: Document) => {
    if (!confirm(`Delete "${doc.filename}"?`)) return;
    
    setDeletingId(doc.source);
    try {
      await apiClient.deleteDocument(doc.source);
      toast.success('Document deleted');
      fetchDocuments();
    } catch (err) {
      toast.error(`Failed to delete: ${getErrorMessage(err)}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleReingest = async (doc: Document) => {
    setReingestingId(doc.source);
    try {
      const result = await apiClient.reingestDocument(doc.source);
      toast.success(`Re-ingested: ${doc.filename} (${result.chunk_count} chunks)`);
      fetchDocuments();
    } catch (err) {
      toast.error(`Failed to re-ingest: ${getErrorMessage(err)}`);
    } finally {
      setReingestingId(null);
    }
  };

  const filteredDocs = search
    ? documents.filter(d => 
        d.filename.toLowerCase().includes(search.toLowerCase()) ||
        d.source.toLowerCase().includes(search.toLowerCase())
      )
    : documents;

  return (
    <div className="space-y-6">
      <Toaster position="top-right" />
      
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Quản lý Tài liệu</h1>
        <p className="text-slate-500 mt-1">Upload, xem và quản lý tài liệu RAG</p>
      </div>

      {/* Upload Zone */}
      <Card>
        <CardContent className="pt-6">
          <div
            {...getRootProps()}
            className={cn(
              'border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer',
              isDragActive ? 'border-primary bg-primary/5' : 'border-slate-200 hover:border-slate-300',
              isUploading && 'opacity-50 cursor-not-allowed'
            )}
          >
            <input {...getInputProps()} />
            {isUploading ? (
              <div className="flex items-center justify-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span>Uploading...</span>
              </div>
            ) : isDragActive ? (
              <div>
                <Upload className="h-10 w-10 mx-auto text-primary mb-2" />
                <p className="text-primary font-medium">Drop files here...</p>
              </div>
            ) : (
              <div>
                <Upload className="h-10 w-10 mx-auto text-slate-400 mb-2" />
                <p className="text-slate-600 font-medium">Drag & drop files here</p>
                <p className="text-sm text-slate-400 mt-1">or click to select</p>
                <p className="text-xs text-slate-400 mt-2">
                  Supported: .txt, .md, .pdf, .docx, .html
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search documents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button variant="outline" onClick={fetchDocuments}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Documents List */}
      <Card>
        <CardHeader>
          <CardTitle>Tài liệu đã upload</CardTitle>
          <CardDescription>
            {total} tài liệu | Trang {page}/{totalPages}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="text-center py-12 text-destructive">
              {error}
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No documents found</p>
              <p className="text-sm">Upload your first document above</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredDocs.map((doc) => (
                <div
                  key={doc.source}
                  className="flex items-center gap-4 p-4 border rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <div className="flex-shrink-0">
                    {fileTypeIcons[doc.file_type] || <File className="h-5 w-5" />}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-slate-900 truncate">{doc.filename}</p>
                      {!doc.is_active && (
                        <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-500 rounded">
                          Deleted
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-500 truncate">{doc.source}</p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                      <span>{formatBytes(doc.file_size)}</span>
                      <span>{doc.chunk_count} chunks</span>
                      <span>{doc.chunk_strategy}</span>
                      <span>{formatDate(doc.uploaded_at)}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleReingest(doc)}
                      disabled={reingestingId === doc.source}
                      title="Re-ingest document"
                    >
                      {reingestingId === doc.source ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(doc)}
                      disabled={deletingId === doc.source}
                      className="text-destructive hover:text-destructive hover:border-destructive"
                      title="Delete document"
                    >
                      {deletingId === doc.source ? (
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
          {totalPages > 1 && (
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
    </div>
  );
}
