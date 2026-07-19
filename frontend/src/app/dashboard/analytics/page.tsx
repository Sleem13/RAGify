"use client";
import { useState, useRef } from 'react';
import { Bar, Pie, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, Download, FileJson, FileSpreadsheet, FileText, ChevronDown, LayoutDashboard } from 'lucide-react';
import { useAppContext } from '@/context/AppContext';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface ChartData {
  id: string;
  title: string;
  type: 'bar' | 'pie' | 'line';
  labels: string[];
  datasets: any[];
}

interface AnalysisData {
  summary: { columns: string[]; rows_count: number; date_columns?: string[] };
  charts?: ChartData[];
  chart_data?: any; // Legacy
  insights: string;
}

export default function AnalyticsDashboard() {
  const { t, theme, language } = useAppContext();
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const dashboardRef = useRef<HTMLDivElement>(null);

  const [analysis] = useState<AnalysisData | null>(() => {
    if (typeof window !== 'undefined') {
      const data = localStorage.getItem('excel_analysis');
      return data ? JSON.parse(data) : null;
    }
    return null;
  });

  const getApiUrl = () => {
    const custom = typeof window !== 'undefined' ? localStorage.getItem('custom_api_url') || '' : '';
    return custom.trim() || process.env.NEXT_PUBLIC_API_URL || '/api/backend';
  };

  const handleExport = async (format: 'json' | 'csv' | 'xlsx' | 'pdf') => {
    if (!analysis) return;
    setExportLoading(true);
    setShowExportMenu(false);
    try {
      if (format === 'pdf') {
        // Simple client-side PDF trigger using browser print (Dashboard view)
        window.print();
        setExportLoading(false);
        return;
      }

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
      a.download = `ragify_dashboard_export.${format}`;
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
        a.download = 'ragify_dashboard_export.json';
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        alert("Export to this format is not supported locally. Download JSON instead.");
      }
    }
    setExportLoading(false);
  };

  if (!analysis) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-950 text-slate-900 dark:text-white flex flex-col items-center justify-center gap-4 transition-colors duration-300">
        <LayoutDashboard className="w-16 h-16 text-indigo-500 mb-4" />
        <h2 className="text-3xl font-bold">AI Analytics Dashboard</h2>
        <p className="text-xl text-gray-500">{t('noData') || 'No data available to analyze.'}</p>
        <Link href="/dashboard" className="text-indigo-600 dark:text-indigo-400 hover:underline mt-4 px-6 py-2 bg-indigo-500/10 rounded-full font-bold">
          Upload Data
        </Link>
      </div>
    );
  }

  const isDark = theme === 'dark';
  
  // Normalize charts array
  const charts: ChartData[] = analysis.charts || (analysis.chart_data ? [{
    id: "legacy_1",
    title: "Data Overview",
    type: analysis.chart_data.type || "bar",
    labels: analysis.chart_data.labels,
    datasets: analysis.chart_data.datasets
  }] : []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 text-slate-900 dark:text-white p-6 transition-colors duration-300 print:bg-white print:text-black">
      <div className="max-w-7xl mx-auto" ref={dashboardRef}>

        {/* Header */}
        <div className="flex justify-between items-center mb-8 print:hidden">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="p-2 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/10 rounded-full transition-colors"
            >
              {language === 'ar' ? <ArrowRight className="w-5 h-5" /> : <ArrowLeft className="w-5 h-5" />}
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <LayoutDashboard className="w-8 h-8 text-indigo-600" />
              Executive Dashboard
            </h1>
          </div>

          {/* Export Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={exportLoading}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl transition-colors font-bold shadow-lg shadow-indigo-500/30"
            >
              <Download className="w-5 h-5" />
              {exportLoading ? 'Processing...' : 'Export Dashboard'}
              <ChevronDown className="w-4 h-4" />
            </button>
            {showExportMenu && (
              <div className="absolute top-full mt-2 end-0 w-56 bg-white dark:bg-slate-900 border border-gray-200 dark:border-white/10 rounded-xl shadow-2xl overflow-hidden z-20">
                <button
                  onClick={() => handleExport('pdf')}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors text-slate-800 dark:text-white text-sm font-medium"
                >
                  <FileText className="w-5 h-5 text-red-500" /> PDF Report (Print)
                </button>
                <div className="h-px bg-gray-100 dark:bg-white/5 my-1" />
                <button
                  onClick={() => handleExport('json')}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors text-slate-800 dark:text-white text-sm font-medium"
                >
                  <FileJson className="w-5 h-5 text-amber-500" /> Raw JSON Data
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors text-slate-800 dark:text-white text-sm font-medium"
                >
                  <FileText className="w-5 h-5 text-emerald-500" /> CSV Export
                </button>
                <button
                  onClick={() => handleExport('xlsx')}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors text-slate-800 dark:text-white text-sm font-medium"
                >
                  <FileSpreadsheet className="w-5 h-5 text-indigo-500" /> Excel Export
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Print Header */}
        <div className="hidden print:block mb-8 text-center border-b pb-4">
          <h1 className="text-4xl font-bold mb-2">RAGify AI Executive Report</h1>
          <p className="text-gray-500">Automatically generated data analysis & insights dashboard.</p>
        </div>

        {/* AI Insights Banner */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-6 mb-8 text-white shadow-lg print:border print:border-gray-300 print:text-black print:bg-none print:shadow-none">
          <h3 className="font-bold text-lg mb-2 flex items-center gap-2">
            ✨ AI Executive Insights
          </h3>
          <p className="leading-relaxed opacity-90 print:opacity-100">{analysis.insights}</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 shadow-sm print:border-gray-300">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm mb-2 font-bold uppercase tracking-wider">Total Rows</h3>
            <p className="text-4xl font-black text-indigo-600 dark:text-indigo-400">{analysis.summary.rows_count.toLocaleString()}</p>
          </div>
          <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 shadow-sm print:border-gray-300">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm mb-2 font-bold uppercase tracking-wider">Total Columns</h3>
            <p className="text-4xl font-black text-purple-600 dark:text-purple-400">{analysis.summary.columns.length}</p>
          </div>
          <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 shadow-sm print:border-gray-300">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm mb-2 font-bold uppercase tracking-wider">Numeric Fields</h3>
            <p className="text-4xl font-black text-emerald-600 dark:text-emerald-400">{analysis.summary.numeric_columns?.length || 0}</p>
          </div>
          <div className="bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 shadow-sm print:border-gray-300">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm mb-2 font-bold uppercase tracking-wider">Categorical Fields</h3>
            <p className="text-4xl font-black text-amber-600 dark:text-amber-400">{analysis.summary.categorical_columns?.length || 0}</p>
          </div>
        </div>

        {/* Dynamic Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {charts.map((chart, index) => (
            <div key={chart.id || index} className={`bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl p-6 shadow-sm print:border-gray-300 print:break-inside-avoid ${chart.type === 'line' ? 'lg:col-span-2' : ''}`}>
              <h2 className="text-xl font-bold mb-6">{chart.title}</h2>
              <div className={chart.type === 'pie' ? "h-[300px] flex justify-center" : "h-[400px]"}>
                {chart.type === 'bar' && (
                  <Bar
                    data={chart as any}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: { display: false },
                      },
                      scales: {
                        y: { ticks: { color: isDark ? '#94a3b8' : '#64748b' }, grid: { color: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.05)' } },
                        x: { ticks: { color: isDark ? '#94a3b8' : '#64748b' }, grid: { display: false } },
                      },
                    }}
                  />
                )}
                {chart.type === 'pie' && (
                  <Pie
                    data={chart as any}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: { position: 'right', labels: { color: isDark ? '#e2e8f0' : '#475569', padding: 20 } },
                      },
                    }}
                  />
                )}
                {chart.type === 'line' && (
                  <Line
                    data={chart as any}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: { display: false },
                      },
                      scales: {
                        y: { ticks: { color: isDark ? '#94a3b8' : '#64748b' }, grid: { color: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.05)' } },
                        x: { ticks: { color: isDark ? '#94a3b8' : '#64748b' }, grid: { display: false } },
                      },
                    }}
                  />
                )}
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
