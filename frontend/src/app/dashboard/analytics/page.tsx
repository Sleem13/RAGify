"use client";
import { useState } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, Download, FileJson, FileSpreadsheet, FileText, ChevronDown } from 'lucide-react';
import { useAppContext } from '@/context/AppContext';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface AnalysisData {
  summary: { columns: string[]; rows_count: number };
  chart_data: {
    type: string;
    labels: string[];
    datasets: { label: string; data: number[]; backgroundColor?: string; borderColor?: string; borderWidth?: number }[];
  } | null;
  insights: string;
}

export default function AnalyticsDashboard() {
  const { t, theme, language } = useAppContext();
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);

  const [analysis] = useState<AnalysisData | null>(() => {
    if (typeof window !== 'undefined') {
      const data = localStorage.getItem('excel_analysis');
      return data ? JSON.parse(data) : null;
    }
    return null;
  });

  const getApiUrl = () => {
    const custom = typeof window !== 'undefined' ? localStorage.getItem('custom_api_url') || '' : '';
    return custom.trim() || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9999';
  };

  const handleExport = async (format: 'json' | 'csv' | 'xlsx') => {
    if (!analysis) return;
    setExportLoading(true);
    setShowExportMenu(false);
    try {
      const formData = new FormData();
      formData.append('format', format);
      formData.append('data', JSON.stringify(analysis));

      const res = await fetch(`${getApiUrl()}/export`, {
        method: 'POST',
        headers: { 'Bypass-Tunnel-Reminder': 'true' },
        body: formData,
      });

      if (!res.ok) throw new Error('Export failed');

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ragify_export.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      // Fallback: JSON download directly from browser
      if (format === 'json') {
        const blob = new Blob([JSON.stringify(analysis, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'ragify_export.json';
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    }
    setExportLoading(false);
  };

  if (!analysis) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-950 text-slate-900 dark:text-white flex flex-col items-center justify-center gap-4 transition-colors duration-300">
        <p className="text-xl">{t('noData')}</p>
        <Link href="/dashboard" className="text-indigo-600 dark:text-indigo-400 hover:underline">
          {t('returnDashboard')}
        </Link>
      </div>
    );
  }

  const isDark = theme === 'dark';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 text-slate-900 dark:text-white p-6 transition-colors duration-300">
      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="p-2 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/10 rounded-full transition-colors"
            >
              {language === 'ar' ? <ArrowRight className="w-5 h-5" /> : <ArrowLeft className="w-5 h-5" />}
            </Link>
            <h1 className="text-3xl font-bold">{t('analyticsDashboard')}</h1>
          </div>

          {/* Export Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={exportLoading}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl transition-colors font-bold"
            >
              <Download className="w-5 h-5" />
              {exportLoading ? t('processing') : t('downloadReport')}
              <ChevronDown className="w-4 h-4" />
            </button>
            {showExportMenu && (
              <div className="absolute top-full mt-2 end-0 w-52 bg-white dark:bg-slate-900 border border-gray-200 dark:border-white/10 rounded-xl shadow-2xl overflow-hidden z-20">
                <button
                  onClick={() => handleExport('json')}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors text-slate-800 dark:text-white text-sm font-medium"
                >
                  <FileJson className="w-5 h-5 text-amber-500" /> JSON
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors text-slate-800 dark:text-white text-sm font-medium border-t border-gray-100 dark:border-white/5"
                >
                  <FileText className="w-5 h-5 text-emerald-500" /> CSV
                </button>
                <button
                  onClick={() => handleExport('xlsx')}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors text-slate-800 dark:text-white text-sm font-medium border-t border-gray-100 dark:border-white/5"
                >
                  <FileSpreadsheet className="w-5 h-5 text-indigo-500" /> Excel (.xlsx)
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 shadow-sm">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm mb-2">{t('totalRows')}</h3>
            <p className="text-4xl font-bold text-indigo-600 dark:text-indigo-400">{analysis.summary.rows_count.toLocaleString()}</p>
          </div>
          <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 shadow-sm">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm mb-2">{t('totalColumns')}</h3>
            <p className="text-4xl font-bold text-purple-600 dark:text-purple-400">{analysis.summary.columns.length}</p>
          </div>
          <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 shadow-sm">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm mb-2">{t('aiInsights')}</h3>
            <p className="text-sm font-medium text-pink-600 dark:text-pink-400 leading-relaxed">{analysis.insights}</p>
          </div>
        </div>

        {/* Detected Columns */}
        <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 mb-6 shadow-sm">
          <h2 className="text-xl font-bold mb-4">{t('detectedColumns')}</h2>
          <div className="flex flex-wrap gap-2">
            {analysis.summary.columns.map((col, i) => (
              <span key={i} className="px-3 py-1 bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 rounded-full text-sm font-medium">
                {col}
              </span>
            ))}
          </div>
        </div>

        {/* Chart */}
        {analysis.chart_data && (
          <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 mb-6 shadow-sm">
            <h2 className="text-xl font-bold mb-6">{t('autoGeneratedChart')}</h2>
            <div className="h-[400px]">
              <Bar
                data={analysis.chart_data}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: { labels: { color: isDark ? '#e2e8f0' : '#475569' } },
                    title: { display: false },
                  },
                  scales: {
                    y: {
                      ticks: { color: isDark ? '#94a3b8' : '#64748b' },
                      grid: { color: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.05)' },
                    },
                    x: {
                      ticks: { color: isDark ? '#94a3b8' : '#64748b' },
                      grid: { color: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.05)' },
                    },
                  },
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
