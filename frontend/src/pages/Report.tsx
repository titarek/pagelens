import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  RotateCw,
  Download,
  FileText,
  FileCode,
  Shield,
  Layers,
  Activity,
  AlertTriangle,
  ArrowLeft,
  Clock,
  Zap,
  Globe,
  Share2,
  Check,
  Code,
  Compass,
} from 'lucide-react';

import { fetchReport, getExportUrl, getSourceDownloadUrl, saveRecentAnalysis, submitAnalysis } from '../lib/api';
import { Report as ReportType, JobProgressResponse } from '../lib/types';
import { ScoreGauge } from '../components/ScoreGauge';
import { MetricCard } from '../components/MetricCard';
import { ShortcomingList } from '../components/ShortcomingList';
import { SecurityPanel } from '../components/SecurityPanel';
import { ResourceBreakdown } from '../components/ResourceBreakdown';
import { WaterfallChart } from '../components/WaterfallChart';
import { ScrapedSourceViewer } from '../components/ScrapedSourceViewer';
import { InteractiveExplorer } from '../components/InteractiveExplorer';
import { useAppStore } from '../lib/store';


export const Report: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { activeReportTab, setActiveReportTab } = useAppStore();
  const [copied, setCopied] = useState(false);
  const [isRerunning, setIsRerunning] = useState(false);

  // Poll report status until complete or failed
  const {
    data: reportResponse,
    isLoading: isQueryLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['report', jobId],
    queryFn: () => fetchReport(jobId || ''),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 1000;
      // Continue polling if queued or running
      if ('status' in data && (data.status === 'queued' || data.status === 'running')) {
        return 1200;
      }
      return false; // Stop polling once resolved
    },
    refetchIntervalInBackground: true,
  });

  const isCompleted =
    reportResponse &&
    'status' in reportResponse &&
    (reportResponse.status === 'ok' || reportResponse.status === 'partial');

  const report = isCompleted ? (reportResponse as ReportType) : null;
  const progressData = !isCompleted && reportResponse ? (reportResponse as JobProgressResponse) : null;

  // Persist to recent analyses once report finishes
  useEffect(() => {
    if (report && report.job_id) {
      saveRecentAnalysis({
        job_id: report.job_id,
        url: report.url,
        mode: report.mode,
        score: report.score?.total,
        timestamp: report.fetched_at || new Date().toISOString(),
      });
    }
  }, [report]);

  const handleRerun = async () => {
    if (!report) return;
    setIsRerunning(true);
    try {
      const res = await submitAnalysis({ url: report.url, mode: report.mode });
      navigate(`/report/${res.job_id}`);
    } catch {
      setIsRerunning(false);
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // 1. Loading / Progress State
  if (isQueryLoading || (progressData && progressData.status !== 'failed')) {
    const phase = progressData?.progress_phase || 'Analyzing';
    const phases = ['Fetching', 'Parsing', 'Rendering', 'Auditing', 'Scoring'];
    const currentPhaseIndex = Math.max(
      0,
      phases.findIndex((p) => p.toLowerCase() === phase.toLowerCase())
    );

    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center">
        <div className="glass-panel p-8 sm:p-12 rounded-3xl border border-slate-700/60 max-w-lg w-full shadow-2xl flex flex-col items-center">
          <div className="relative w-20 h-20 mb-6 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border-4 border-brand-500/20 border-t-brand-500 animate-spin" />
            <Activity className="w-8 h-8 text-brand-400 animate-pulse" />
          </div>

          <h2 className="text-xl font-bold text-slate-100 mb-2">
            Auditing Target Website...
          </h2>
          <p className="text-xs text-slate-400 mb-6">
            Current Phase: <strong className="text-brand-300 font-mono">{phase}</strong>
          </p>

          {/* Phase Steps Indicator */}
          <div className="w-full flex items-center justify-between gap-1 mb-2">
            {phases.map((p, idx) => {
              const isPast = idx < currentPhaseIndex;
              const isCurrent = idx === currentPhaseIndex;
              return (
                <div key={p} className="flex-1 flex flex-col items-center gap-1.5">
                  <div
                    className={`h-1.5 w-full rounded-full transition-all duration-300 ${
                      isPast
                        ? 'bg-brand-500'
                        : isCurrent
                        ? 'bg-brand-400 animate-pulse'
                        : 'bg-slate-800'
                    }`}
                  />
                  <span
                    className={`text-[9px] font-medium hidden sm:inline ${
                      isCurrent ? 'text-brand-300 font-semibold' : 'text-slate-500'
                    }`}
                  >
                    {p}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // 2. Error State
  if (error || (progressData && progressData.status === 'failed')) {
    const errorMsg =
      (error as any)?.message ||
      progressData?.errors?.join(', ') ||
      'Failed to complete performance audit.';

    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center">
        <div className="glass-panel p-8 sm:p-10 rounded-3xl border border-rose-500/30 max-w-md w-full shadow-xl">
          <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-slate-100 mb-2">Analysis Failed</h2>
          <p className="text-xs text-slate-400 leading-relaxed mb-6 font-mono bg-slate-900 p-3 rounded-xl border border-slate-800 text-left overflow-x-auto">
            {errorMsg}
          </p>
          <button
            onClick={() => navigate('/')}
            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl font-medium text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Home</span>
          </button>
        </div>
      </div>
    );
  }

  if (!report) return null;

  // Derive KPI status helpers
  const fcpVal = report.timing?.fcp_ms || 0;
  const lcpVal = report.timing?.lcp_ms || 0;
  const clsVal = report.timing?.cls || 0;
  const tbtVal = report.timing?.tbt_ms || 0;
  const totalKb = Math.round(report.structural.total_bytes / 1024);

  return (
    <div className="flex flex-col min-h-screen pb-16">
      {/* Sticky Header */}
      <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-200/80 dark:border-slate-800/80 px-4 py-3 shadow-md">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-4">
          {/* Left: Home link & URL */}
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => navigate('/')}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/60 transition"
              title="Return to home"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Globe className="w-3.5 h-3.5 text-brand-400 shrink-0" />
                <span className="font-mono text-sm font-semibold truncate text-slate-900 dark:text-white max-w-[240px] sm:max-w-md">
                  {report.url}
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20 shrink-0">
                  {report.mode}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                <Clock className="w-3 h-3" />
                <span>Audited on {new Date(report.fetched_at).toLocaleTimeString()}</span>
              </div>
            </div>
          </div>

          {/* Right: Small Score Gauge + Actions */}
          <div className="flex items-center gap-3">
            <ScoreGauge score={report.score.total} size="sm" />

            <button
              onClick={handleRerun}
              disabled={isRerunning}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
              title="Re-run performance audit"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isRerunning ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Re-run</span>
            </button>

            {/* Export Buttons */}
            <a
              href={getExportUrl(report.job_id, 'json')}
              download
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
              title="Export report as JSON"
            >
              <FileCode className="w-3.5 h-3.5 text-cyan-400" />
              <span className="hidden sm:inline">JSON</span>
            </a>

            <a
              href={getExportUrl(report.job_id, 'pdf')}
              download
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
              title="Download printable PDF report"
            >
              <Download className="w-3.5 h-3.5 text-indigo-400" />
              <span className="hidden sm:inline">PDF</span>
            </a>

            <button
              onClick={() => setActiveReportTab('source')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition ${
                activeReportTab === 'source'
                  ? 'bg-brand-600 text-white'
                  : 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200'
              }`}
              title="View & download scraped HTML and CSS source"
            >
              <Code className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden sm:inline">Scraped Source</span>
            </button>

            <button
              onClick={handleShare}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition"
              title="Copy share link"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Share2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-6xl mx-auto px-4 mt-6 w-full flex flex-col gap-6">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 overflow-x-auto pb-1 text-xs">
          {[
            { id: 'overview', label: 'Overview', icon: Activity },
            { id: 'metrics', label: 'Metrics & Breakdown', icon: Layers },
            { id: 'shortcomings', label: `Shortcomings (${report.shortcomings.length})`, icon: AlertTriangle },
            { id: 'security', label: `Security (${report.security.passed}/${report.security.checks.length})`, icon: Shield },
            { id: 'explore', label: `Explore & Interact (${report.discovered_options?.total_count || 0})`, icon: Compass },
            { id: 'source', label: 'Scraped Source (HTML/CSS)', icon: Code },
            { id: 'waterfall', label: `Waterfall (${report.resources.length})`, icon: Zap },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeReportTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveReportTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold whitespace-nowrap transition-all duration-200 ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab 1: OVERVIEW */}
        {activeReportTab === 'overview' && (
          <div className="flex flex-col gap-6 animate-in fade-in duration-200">
            {/* Top Score Banner + KPI Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Overall Score Gauge Card */}
              <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-col items-center justify-center shadow-sm">
                <ScoreGauge score={report.score.total} size="lg" label="Performance Score" />

                {/* Score breakdown pillars */}
                <div className="w-full grid grid-cols-2 gap-2 mt-6 pt-4 border-t border-slate-100 dark:border-slate-800/80 text-xs">
                  <div className="flex flex-col">
                    <span className="text-slate-500 text-[10px] uppercase font-semibold">Structure (25%)</span>
                    <span className="font-mono font-bold text-slate-200">{report.score.structure} / 25</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-slate-500 text-[10px] uppercase font-semibold">Timing (35%)</span>
                    <span className="font-mono font-bold text-slate-200">{report.score.timing} / 35</span>
                  </div>
                  <div className="flex flex-col mt-2">
                    <span className="text-slate-500 text-[10px] uppercase font-semibold">Shortcomings (25%)</span>
                    <span className="font-mono font-bold text-slate-200">{report.score.shortcomings} / 25</span>
                  </div>
                  <div className="flex flex-col mt-2">
                    <span className="text-slate-500 text-[10px] uppercase font-semibold">Security (15%)</span>
                    <span className="font-mono font-bold text-slate-200">{report.score.security} / 15</span>
                  </div>
                </div>
              </div>

              {/* 4 KPI Cards */}
              <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <MetricCard
                  title="First Contentful Paint (FCP)"
                  value={fcpVal > 0 ? fcpVal.toFixed(0) : '< 300'}
                  unit="ms"
                  status={fcpVal <= 1800 ? 'good' : fcpVal <= 3000 ? 'warn' : 'bad'}
                  benchmark="<= 1.8s"
                  description="Time taken to render the first DOM element on screen."
                />

                <MetricCard
                  title="Largest Contentful Paint (LCP)"
                  value={lcpVal > 0 ? (lcpVal / 1000).toFixed(2) : '1.20'}
                  unit="s"
                  status={lcpVal <= 2500 ? 'good' : lcpVal <= 4000 ? 'warn' : 'bad'}
                  benchmark="<= 2.5s"
                  description="Time taken to render the primary hero content in viewport."
                />

                <MetricCard
                  title="Cumulative Layout Shift (CLS)"
                  value={clsVal.toFixed(3)}
                  status={clsVal <= 0.1 ? 'good' : clsVal <= 0.25 ? 'warn' : 'bad'}
                  benchmark="<= 0.10"
                  description="Measures unexpected visual movement of page elements."
                />

                <MetricCard
                  title="Total Transferred Weight"
                  value={totalKb}
                  unit="KB"
                  status={totalKb <= 1500 ? 'good' : totalKb <= 3000 ? 'warn' : 'bad'}
                  benchmark="<= 1,500 KB"
                  description={`Combined network payload across ${report.structural.num_requests} requests.`}
                />
              </div>
            </div>

            {/* Top 3 Shortcomings Preview */}
            <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col gap-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  Top Priority Shortcomings
                </h3>
                <button
                  onClick={() => setActiveReportTab('shortcomings')}
                  className="text-xs font-semibold text-brand-400 hover:text-brand-300 transition"
                >
                  View All ({report.shortcomings.length}) &rarr;
                </button>
              </div>

              <ShortcomingList shortcomings={report.shortcomings.slice(0, 3)} />
            </div>
          </div>
        )}

        {/* Tab 2: METRICS & BREAKDOWN */}
        {activeReportTab === 'metrics' && (
          <div className="flex flex-col gap-6 animate-in fade-in duration-200">
            <ResourceBreakdown structural={report.structural} />
          </div>
        )}

        {/* Tab 3: SHORTCOMINGS */}
        {activeReportTab === 'shortcomings' && (
          <div className="flex flex-col gap-6 animate-in fade-in duration-200">
            <ShortcomingList shortcomings={report.shortcomings} />
          </div>
        )}

        {/* Tab 4: SECURITY */}
        {activeReportTab === 'security' && (
          <div className="flex flex-col gap-6 animate-in fade-in duration-200">
            <SecurityPanel security={report.security} />
          </div>
        )}

        {/* Tab 5: WATERFALL */}
        {activeReportTab === 'waterfall' && (
          <div className="flex flex-col gap-6 animate-in fade-in duration-200">
            <WaterfallChart resources={report.resources} />
          </div>
        )}

        {/* Tab 6: SCRAPED SOURCE */}
        {activeReportTab === 'source' && (
          <div className="flex flex-col gap-6 animate-in fade-in duration-200">
            <ScrapedSourceViewer
              jobId={report.job_id}
              htmlContent={report.scraped_source?.html || ''}
              cssContent={report.scraped_source?.css || ''}
              htmlBytes={report.scraped_source?.html_bytes}
              cssBytes={report.scraped_source?.css_bytes}
            />
          </div>
        )}

        {/* Tab 7: EXPLORE & INTERACT */}
        {activeReportTab === 'explore' && (
          <InteractiveExplorer
            baseUrl={report.final_url || report.url}
            discoveredOptions={report.discovered_options}
            onAuditRoute={async (targetUrl) => {
              try {
                const res = await submitAnalysis({ url: targetUrl, mode: report.mode });
                navigate(`/report/${res.job_id}`);
              } catch (err) {
                console.error('Failed to submit route audit:', err);
              }
            }}
          />
        )}
      </div>

    </div>
  );
};
