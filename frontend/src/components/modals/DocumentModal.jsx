import React, { useState, useEffect } from 'react';
import { X, UploadCloud, FileText, Trash2, Check, Paperclip, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { useChat } from '../../contexts/ChatContext';

export function DocumentModal({ isOpen, onClose, theme }) {
  const isLight = theme === 'lavender-glow';
  const { attachedFiles, setAttachedFiles } = useChat();
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const fetchDocs = async () => {
    try {
      const docs = await api.listDocuments();
      setDocuments(docs);
    } catch (err) {
      console.warn('Failed to load documents:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDocs();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setUploading(true);
    try {
      const newDoc = await api.uploadDocument(file);
      setDocuments((prev) => [newDoc, ...prev]);
      if (!attachedFiles.some((f) => f.id === newDoc.id)) {
        setAttachedFiles((prev) => [...prev, newDoc]);
      }
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setAttachedFiles((prev) => prev.filter((f) => f.id !== id));
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const toggleAttach = (doc) => {
    if (attachedFiles.some((f) => f.id === doc.id)) {
      setAttachedFiles((prev) => prev.filter((f) => f.id !== doc.id));
    } else {
      setAttachedFiles((prev) => [...prev, doc]);
    }
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm ${
      isLight ? 'bg-slate-900/30' : 'bg-black/70'
    }`}>
      <div className={`relative w-full max-w-xl rounded-2xl border shadow-2xl p-4 sm:p-6 flex flex-col max-h-[90dvh] transition-colors ${
        isLight
          ? 'bg-white text-slate-900 border-purple-200/90 shadow-purple-950/10'
          : 'bg-slate-900 border-slate-800 text-slate-100 shadow-2xl'
      }`}>
        {/* Header */}
        <div className={`flex items-center justify-between pb-4 border-b ${
          isLight ? 'border-purple-100' : 'border-slate-800'
        }`}>
          <div className="flex items-center gap-2">
            <FileText size={18} className="text-purple-500" />
            <h2 className={`text-base font-bold ${
              isLight ? 'text-slate-900' : 'text-white'
            }`}>
              Document Knowledge Base (RAG)
            </h2>
          </div>
          <button
            onClick={onClose}
            className={`p-1.5 rounded-lg transition-colors ${
              isLight
                ? 'text-slate-400 hover:text-slate-900 hover:bg-purple-50'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <X size={18} />
          </button>
        </div>

        <p className={`text-xs mt-2 mb-4 ${
          isLight ? 'text-slate-500' : 'text-slate-400'
        }`}>
          Upload reference documents (.txt, .md, .csv, .json, .py, .js, .pdf) to automatically ground AI answers with chunked retrieval.
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle size={15} className="flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Upload Dropzone */}
        <label className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center ${
          isLight
            ? 'border-purple-200 hover:border-purple-400 bg-purple-50/40 hover:bg-purple-50/80 text-purple-950'
            : 'border-slate-700 hover:border-brand-500 bg-slate-950/50 hover:bg-slate-850/50 text-slate-300'
        }`}>
          <input
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
            accept=".txt,.md,.markdown,.csv,.json,.py,.js,.html,.css,.pdf"
            className="hidden"
          />
          {uploading ? (
            <Loader2 size={24} className="animate-spin text-purple-600 mb-2" />
          ) : (
            <UploadCloud size={24} className={isLight ? 'text-purple-500 mb-2' : 'text-brand-400 mb-2'} />
          )}
          <span className="text-xs font-semibold">
            {uploading ? 'Processing & Indexing Chunks...' : 'Click or drop files to upload'}
          </span>
          <span className={`text-[10px] mt-1 ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
            Max 20MB per document. Automatically chunked for RAG search.
          </span>
        </label>

        {/* Uploaded Documents List */}
        <div className="mt-5 flex-1 overflow-y-auto space-y-2">
          <div className={`text-xs font-semibold uppercase tracking-wider mb-2 ${
            isLight ? 'text-slate-500' : 'text-slate-400'
          }`}>
            Indexed Documents ({documents.length})
          </div>

          {documents.length === 0 ? (
            <div className={`text-center py-8 text-xs ${
              isLight ? 'text-slate-400' : 'text-slate-500'
            }`}>
              No documents in knowledge base yet.
            </div>
          ) : (
            documents.map((doc) => {
              const isAttached = attachedFiles.some((f) => f.id === doc.id);
              return (
                <div
                  key={doc.id}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-all ${
                    isLight
                      ? 'bg-purple-50/40 hover:bg-purple-50/80 border-purple-200/80'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText size={16} className="text-purple-500 flex-shrink-0" />
                    <div className="truncate">
                      <div className={`text-xs font-semibold truncate ${
                        isLight ? 'text-slate-900' : 'text-slate-200'
                      }`}>
                        {doc.filename}
                      </div>
                      <div className={`text-[10px] ${
                        isLight ? 'text-slate-500' : 'text-slate-400'
                      }`}>
                        {formatSize(doc.file_size)} • {doc.chunk_count || 1} chunks
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggleAttach(doc)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors flex items-center gap-1 ${
                        isAttached
                          ? isLight
                            ? 'bg-purple-100 border-purple-300 text-purple-900'
                            : 'bg-brand-600/20 border-brand-500/50 text-brand-300'
                          : isLight
                          ? 'border-purple-200 text-slate-600 hover:bg-purple-100 hover:text-slate-900'
                          : 'border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                      title={isAttached ? 'Attached to current chat' : 'Attach to current chat'}
                    >
                      {isAttached ? <Check size={12} /> : <Paperclip size={12} />}
                      <span>{isAttached ? 'Attached' : 'Attach'}</span>
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className={`p-1.5 rounded-lg transition-colors ${
                        isLight
                          ? 'text-slate-400 hover:text-rose-600 hover:bg-rose-50'
                          : 'text-slate-400 hover:text-rose-400 hover:bg-slate-800'
                      }`}
                      title="Delete document"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
