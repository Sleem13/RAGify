"use client";
import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  UploadCloud, MessageSquare, BarChart3, Send, Settings, Check,
  Sun, Moon, Languages, Home, Key, Copy, Trash2, RefreshCw,
  FileText, FileSpreadsheet, Image, X, FolderOpen, ChevronRight
} from 'lucide-react';
import Link from 'next/link';
import { useAppContext } from '@/context/AppContext';

interface Message {
  role: 'user' | 'system';
  content: string;
  action?: string | null;
  timestamp?: number;
}

interface IndexedFile {
  type: 'document' | 'excel';
  chunks: number;
}

export default function Dashboard() {
  const { t, theme, toggleTheme, language, toggleLanguage } = useAppContext();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Messages with localStorage persistence
  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('ragify_chat_history');
        if (saved) return JSON.parse(saved);
      } catch {}
    }
    return [{ role: 'system', content: 'Hello! Upload your files and I will be ready to answer your questions or analyze your data.', timestamp: Date.now() }];
  });

  // File registry from backend
  const [indexedFiles, setIndexedFiles] = useState<Record<string, IndexedFile>>({});
  const [hasExcelData, setHasExcelData] = useState(false);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const [showSettings, setShowSettings] = useState(false);
  const [customApiUrl, setCustomApiUrl] = useState(() => {
    if (typeof window !== 'undefined') return localStorage.getItem('custom_api_url') || '';
    return '';
  });

  const [showApiKey, setShowApiKey] = useState(false);
  const [generatedKey, setGeneratedKey] = useState('');
  const [keyCopied, setKeyCopied] = useState(false);
  const [keyLoading, setKeyLoading] = useState(false);
  const [showFiles, setShowFiles] = useState(false);

  // ── Helpers ───────────────────────────────────────────────────────────────

  const getApiUrl = () =>
    customApiUrl.trim() || process.env.NEXT_PUBLIC_API_URL || '/api/backend';

  const getAxiosConfig = () => ({
    headers: { "Bypass-Tunnel-Reminder": "true" }
  });

  const saveApiUrl = () => {
    localStorage.setItem('custom_api_url', customApiUrl.trim());
    setShowSettings(false);
  };

  // ── Scroll to bottom ──────────────────────────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // ── Persist chat to localStorage ──────────────────────────────────────────

  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Keep only last 50 messages to avoid localStorage overflow
      const toSave = messages.slice(-50);
      localStorage.setItem('ragify_chat_history', JSON.stringify(toSave));
    }
  }, [messages]);

  // ── Fetch indexed files from backend ─────────────────────────────────────

  const fetchFiles = async () => {
    try {
      const res = await axios.get(`${getApiUrl()}/files`, getAxiosConfig());
      setIndexedFiles(res.data.files || {});
      const hasExcel = Object.values(res.data.files || {}).some(
        (f: any) => f.type === 'excel'
      );
      setHasExcelData(hasExcel);
    } catch {
      // Backend might not be up yet
    }
  };

  useEffect(() => {
    fetchFiles();
    // Also restore excel data flag from localStorage
    if (typeof window !== 'undefined' && localStorage.getItem('excel_analysis')) {
      setHasExcelData(true);
    }
  }, []);

  // ── File icon helper ───────────────────────────────────────────────────────

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    if (['xlsx', 'xls', 'csv'].includes(ext)) return <FileSpreadsheet className="w-4 h-4 text-emerald-500" />;
    if (['png', 'jpg', 'jpeg'].includes(ext)) return <Image className="w-4 h-4 text-pink-500" />;
    return <FileText className="w-4 h-4 text-indigo-500" />;
  };

  // ── API Key ────────────────────────────────────────────────────────────────

  const handleGenerateKey = async () => {
    setKeyLoading(true);
    try {
      const res = await axios.post(`${getApiUrl()}/generate-api-key`, {}, getAxiosConfig());
      setGeneratedKey(res.data.api_key);
    } catch {
      setGeneratedKey('Error: Could not connect to backend.');
    }
    setKeyLoading(false);
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText(generatedKey);
    setKeyCopied(true);
    setTimeout(() => setKeyCopied(false), 2000);
  };

  // ── Drag and Drop ─────────────────────────────────────────────────────────

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  };

  // ── File upload ───────────────────────────────────────────────────────────

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await axios.post(`${getApiUrl()}/upload`, formData, getAxiosConfig());
      setMessages(prev => [...prev, {
        role: 'system',
        content: res.data.message || 'File uploaded successfully.',
        timestamp: Date.now()
      }]);
      if (res.data.type === 'excel') {
        setHasExcelData(true);
        localStorage.setItem('excel_analysis', JSON.stringify(res.data.analysis));
      }
      setFile(null);
      await fetchFiles();
    } catch {
      setMessages(prev => [...prev, {
        role: 'system',
        content: '❌ Error uploading file. Make sure the backend is running.',
        timestamp: Date.now()
      }]);
    }
    setLoading(false);
  };

  // ── Delete file from registry ─────────────────────────────────────────────

  const handleDeleteFile = async (filename: string) => {
    try {
      await axios.delete(`${getApiUrl()}/files/${encodeURIComponent(filename)}`, getAxiosConfig());
      await fetchFiles();
    } catch {
      // ignore
    }
  };

  // ── Reset knowledge base ──────────────────────────────────────────────────

  const handleReset = async () => {
    if (!confirm('Are you sure? This will delete all uploaded documents from memory.')) return;
    try {
      await axios.delete(`${getApiUrl()}/reset`, getAxiosConfig());
      setMessages([{
        role: 'system',
        content: '✅ Knowledge base reset. All documents have been removed.',
        timestamp: Date.now()
      }]);
      setHasExcelData(false);
      setIndexedFiles({});
      localStorage.removeItem('excel_analysis');
      localStorage.removeItem('ragify_chat_history');
    } catch {
      setMessages(prev => [...prev, {
        role: 'system',
        content: '❌ Could not reset. Check backend connection.',
        timestamp: Date.now()
      }]);
    }
  };

  // ── Chat with conversation memory ─────────────────────────────────────────

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    const newUserMessage: Message = { role: 'user', content: userMsg, timestamp: Date.now() };
    const updatedMessages = [...messages, newUserMessage];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);

    try {
      // Build history for the API (exclude the welcome message + last user msg)
      const historyForApi = updatedMessages
        .slice(1, -1) // skip first welcome and last (just-added) user msg
        .filter(m => m.content && !m.content.startsWith('❌') && !m.content.startsWith('✅'))
        .slice(-16)
        .map(m => ({ role: m.role, content: m.content }));

      const formData = new FormData();
      formData.append('message', userMsg);
      formData.append('history', JSON.stringify(historyForApi));

      const res = await axios.post(`${getApiUrl()}/chat`, formData, getAxiosConfig());
      setMessages(prev => [...prev, {
        role: 'system',
        content: res.data.response,
        action: res.data.action,
        timestamp: Date.now()
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'system',
        content: '❌ Could not connect to the server. Check backend URL settings.',
        timestamp: Date.now()
      }]);
    }
    setLoading(false);
  };

  // ─────────────────────────────────────────────────────────────────────────

  const fileCount = Object.keys(indexedFiles).length;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 text-slate-900 dark:text-white p-4 md:p-6 transition-colors duration-300">

      {/* Header */}
      <div className="max-w-7xl mx-auto flex justify-between items-center mb-5">
        <Link href="/" className="flex items-center gap-2 text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-80 transition-opacity">
          <Home className="w-6 h-6 text-indigo-500" />
          {t('appName')}
        </Link>
        <div className="flex gap-2">
          <button onClick={toggleLanguage} className="p-2 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/10 rounded-lg transition-colors text-gray-600 dark:text-gray-400 flex items-center gap-1.5 text-sm font-medium px-3">
            <Languages className="w-4 h-4" />
            {language === 'en' ? 'عربي' : 'EN'}
          </button>
          <button onClick={toggleTheme} className="p-2 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/10 rounded-lg transition-colors text-gray-600 dark:text-gray-400">
            {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-5" style={{ height: 'calc(100vh - 100px)' }}>

        {/* ── Sidebar ── */}
        <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-5 flex flex-col gap-4 overflow-y-auto shadow-sm">

          {/* Upload Area */}
          <div>
            <h2 className="text-base font-bold flex items-center gap-2 mb-3">
              <UploadCloud className="text-indigo-500 w-5 h-5" /> {t('uploadFiles')}
            </h2>
            <div
              className={`border-2 border-dashed rounded-xl p-5 text-center transition-colors cursor-pointer ${isDragging ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10' : 'border-gray-300 dark:border-white/20 hover:border-indigo-400/60'}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => document.getElementById('fileInput')?.click()}
            >
              <input
                type="file"
                className="hidden"
                id="fileInput"
                accept=".pdf,.xlsx,.xls,.csv,.docx,.txt,.pptx,.png,.jpg,.jpeg,.json"
                onChange={(e) => e.target.files && setFile(e.target.files[0])}
              />
              {file ? (
                <div className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-500/20 rounded-full flex items-center justify-center">
                    <FileText className="w-5 h-5 text-indigo-600" />
                  </div>
                  <p className="text-sm font-semibold text-indigo-700 dark:text-indigo-400 break-all">{file.name}</p>
                  <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 py-2">
                  <UploadCloud className="w-8 h-8 text-gray-400" />
                  <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">Drop file or click to select</p>
                  <p className="text-xs text-gray-400">PDF · DOCX · PPTX · TXT · Excel · CSV · Images</p>
                </div>
              )}
            </div>
            <button
              onClick={handleUpload}
              disabled={!file || loading}
              className="mt-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white font-bold py-2.5 px-4 rounded-xl transition-colors w-full flex items-center justify-center gap-2 text-sm"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
              {loading ? t('processing') : t('processFile')}
            </button>
          </div>

          {/* Indexed Files */}
          <div className="border-t border-gray-100 dark:border-white/10 pt-4">
            <button
              onClick={() => setShowFiles(!showFiles)}
              className="w-full flex items-center justify-between text-sm font-bold text-gray-700 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
            >
              <span className="flex items-center gap-2">
                <FolderOpen className="w-4 h-4" />
                Indexed Files ({fileCount})
              </span>
              <ChevronRight className={`w-4 h-4 transition-transform ${showFiles ? 'rotate-90' : ''}`} />
            </button>
            {showFiles && (
              <div className="mt-3 space-y-2">
                {fileCount === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-2">No files indexed yet</p>
                ) : (
                  Object.entries(indexedFiles).map(([name, info]) => (
                    <div key={name} className="flex items-center justify-between gap-2 bg-gray-50 dark:bg-white/5 rounded-lg px-3 py-2">
                      <div className="flex items-center gap-2 overflow-hidden">
                        {getFileIcon(name)}
                        <span className="text-xs text-gray-700 dark:text-gray-300 truncate">{name}</span>
                      </div>
                      <button
                        onClick={() => handleDeleteFile(name)}
                        className="text-red-400 hover:text-red-600 flex-shrink-0"
                        title="Remove from registry"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Analytics Dashboard Button */}
          {hasExcelData && (
            <Link
              href="/dashboard/analytics"
              target="_blank"
              className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2.5 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 text-sm shadow-lg shadow-purple-500/20"
            >
              <BarChart3 className="w-4 h-4" /> {t('viewAnalytics')}
            </Link>
          )}

          {/* API Key Button */}
          <button
            onClick={() => { setShowApiKey(!showApiKey); setShowSettings(false); }}
            className="flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-indigo-500/40 bg-indigo-500/5 hover:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 font-semibold transition-colors text-sm"
          >
            <Key className="w-4 h-4" /> {t('generateApiKey')}
          </button>

          {/* API Key Panel (Inline) */}
          {showApiKey && (
            <div className="bg-gray-50 dark:bg-black/30 border border-gray-200 dark:border-white/10 rounded-xl p-4 text-sm">
              <h3 className="font-bold mb-1 flex items-center gap-2"><Key className="w-4 h-4 text-indigo-500" /> {t('apiKeyTitle')}</h3>
              <p className="text-xs text-gray-500 mb-3">{t('apiKeyDesc')}</p>
              {generatedKey ? (
                <>
                  <div className="bg-white dark:bg-black/40 border border-gray-200 dark:border-white/10 rounded-lg p-2 font-mono text-xs break-all text-slate-800 dark:text-green-400 mb-2">{generatedKey}</div>
                  <div className="flex gap-2">
                    <button onClick={handleCopyKey} className="flex-1 flex items-center justify-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white py-1.5 rounded-lg text-xs font-semibold">
                      {keyCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      {keyCopied ? 'Copied!' : 'Copy Key'}
                    </button>
                    <button onClick={handleGenerateKey} className="p-1.5 border border-gray-200 dark:border-white/10 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10">
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </>
              ) : (
                <button onClick={handleGenerateKey} disabled={keyLoading} className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold py-2 rounded-lg flex items-center justify-center gap-2 text-xs">
                  {keyLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Key className="w-3.5 h-3.5" />}
                  Generate Key
                </button>
              )}
            </div>
          )}

          {/* Reset Button */}
          <button
            onClick={handleReset}
            className="flex items-center justify-center gap-2 py-2 px-4 rounded-xl border border-red-500/30 text-red-500 hover:bg-red-500/10 transition-colors text-sm font-medium mt-auto"
          >
            <Trash2 className="w-4 h-4" /> {t('resetMemory')}
          </button>
        </div>

        {/* ── Chat Area ── */}
        <div className="md:col-span-2 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl flex flex-col overflow-hidden shadow-xl dark:shadow-indigo-900/20">

          {/* Chat Header */}
          <div className="p-4 border-b border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-black/20 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2">
              <MessageSquare className="text-indigo-500 w-5 h-5" />
              <h2 className="text-base font-bold">{t('aiAssistant')}</h2>
              {fileCount > 0 && (
                <span className="text-xs bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 px-2 py-0.5 rounded-full font-medium">
                  {fileCount} file{fileCount > 1 ? 's' : ''} indexed
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {messages.length > 1 && (
                <button
                  onClick={() => {
                    setMessages([{ role: 'system', content: 'Hello! Upload your files and I will be ready to answer your questions or analyze your data.', timestamp: Date.now() }]);
                    localStorage.removeItem('ragify_chat_history');
                  }}
                  className="text-xs text-gray-400 hover:text-red-400 transition-colors flex items-center gap-1"
                  title="Clear chat"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Clear chat
                </button>
              )}
              <button
                onClick={() => { setShowSettings(!showSettings); setShowApiKey(false); }}
                className="p-2 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/10 rounded-lg transition-colors text-gray-600 dark:text-gray-400"
                title="API Settings"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Settings Panel */}
          {showSettings && (
            <div className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-500/30 p-4 flex-shrink-0">
              <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-2">{t('localtunnelUrl')}</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customApiUrl}
                  onChange={e => setCustomApiUrl(e.target.value)}
                  placeholder="https://ragify-backend.loca.lt"
                  className="flex-1 bg-white dark:bg-black/50 border border-gray-300 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 text-slate-900 dark:text-white"
                />
                <button onClick={saveApiUrl} className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded-lg"><Check className="w-4 h-4" /></button>
              </div>
              <p className="text-xs text-gray-500 mt-1.5">{t('leaveEmpty')}</p>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl p-4 shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-none'
                      : 'bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-slate-800 dark:text-gray-200 rounded-bl-none'
                  }`}
                  style={{ direction: /[\u0600-\u06FF]/.test(msg.content) ? 'rtl' : 'ltr' }}
                >
                  <p className="whitespace-pre-wrap leading-relaxed text-sm">{msg.content}</p>

                  {msg.action === 'GENERATE_DASHBOARD' && (
                    <div className="mt-3 pt-3 border-t border-white/20 dark:border-gray-600">
                      <Link
                        href="/dashboard/analytics"
                        target="_blank"
                        className="inline-flex items-center gap-2 bg-white text-indigo-700 hover:bg-indigo-50 font-bold py-2 px-4 rounded-xl transition-colors shadow-md text-sm"
                      >
                        <BarChart3 className="w-4 h-4" />
                        Open Executive Dashboard ↗
                      </Link>
                    </div>
                  )}
                </div>
                {msg.timestamp && (
                  <span className="text-[10px] text-gray-400 mt-1 px-2">
                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 dark:bg-white/10 rounded-2xl rounded-bl-none p-4">
                  <div className="flex gap-1.5 items-center">
                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-black/20 flex-shrink-0">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder={t('askAnything')}
                className="flex-1 bg-white dark:bg-white/5 border border-gray-300 dark:border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors text-slate-900 dark:text-white placeholder:text-gray-400 text-sm"
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="bg-indigo-600 hover:bg-indigo-700 text-white p-3.5 rounded-xl transition-colors disabled:opacity-40 flex-shrink-0"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
