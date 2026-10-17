import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Zap, Gauge, Terminal, ExternalLink, ArrowRight, Clock, Trash2 } from 'lucide-react';
import { UrlInput } from '../components/UrlInput';
import { submitAnalysis, getRecentAnalyses } from '../lib/api';
import { AnalysisMode, RecentAnalysis } from '../lib/types';
import { getScoreColor } from '../components/ScoreGauge';

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentList, setRecentList] = useState<RecentAnalysis[]>([]);

  useEffect(() => {
    setRecentList(getRecentAnalyses());
  }, []);

  const handleAnalyze = async (url: string, mode: AnalysisMode) => {
    setIsLoading(true);
    setError(null);

    try {
      const res = await submitAnalysis({ url, mode });
      // Navigate to report page immediately to track progress
      navigate(`/report/${res.job_id}`);
    } catch (err: any) {
      setError(err?.message || 'Failed to submit analysis. Please check the URL and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    localStorage.removeItem('pagelens_recent_analyses');
    setRecentList([]);
  };

  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-16 sm:py-24 text-center max-w-4xl mx-auto w-full">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/20 mb-6 shadow-sm">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span>PageLens v1.0 — Real-Time Performance & Security Intelligence</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.15]">
          Analyze any URL's{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 via-indigo-400 to-cyan-400">
            performance and security.
          </span>
        </h1>

        <p className="mt-4 text-base sm:text-lg text-slate-600 dark:text-slate-400 max-w-2xl leading-relaxed">
          Deep headless Playwright Chromium rendering, 18+ automated architectural shortcoming rules, Core Web Vitals audit, and TLS header hygiene in one click.
        </p>

        {/* Input Form */}
        <div className="w-full mt-10">
          <UrlInput onAnalyze={handleAnalyze} isLoading={isLoading} error={error} />
        </div>

        {/* Recent Analyses List */}
        {recentList.length > 0 && (
          <div className="w-full max-w-2xl mt-12 text-left">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                Recent Audits
              </span>
              <button
                type="button"
                onClick={handleClearHistory}
                className="text-[11px] text-slate-500 hover:text-rose-400 flex items-center gap-1 transition"
                title="Clear audit history"
              >
                <Trash2 className="w-3 h-3" />
                <span>Clear</span>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {recentList.map((item) => {
                const colorMeta = item.score !== undefined ? getScoreColor(item.score) : null;
                return (
                  <button
                    key={item.job_id}
                    onClick={() => navigate(`/report/${item.job_id}`)}
                    className="flex items-center justify-between p-3 rounded-xl glass-panel border border-slate-200 dark:border-slate-800/80 hover:border-brand-500/50 hover:bg-slate-800/40 transition group text-left"
                  >
                    <div className="truncate mr-2">
                      <div className="font-mono text-xs text-slate-200 truncate group-hover:text-brand-300">
                        {item.url}
                      </div>
                      <div className="text-[10px] text-slate-500 uppercase mt-0.5">
                        {item.mode} mode
                      </div>
                    </div>

                    {item.score !== undefined && colorMeta && (
                      <span
                        className={`shrink-0 font-mono text-xs font-bold px-2 py-0.5 rounded border ${colorMeta.bgClass}`}
                      >
                        {item.score}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Feature Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full mt-16 pt-12 border-t border-slate-200 dark:border-slate-800/80 text-left">
          <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="w-9 h-9 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mb-3">
              <Gauge className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Core Web Vitals & 4G
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
              Synthetically throttles 4x CPU and Slow 4G mobile profiles to measure real-world FCP, LCP, CLS, and TBT.
            </p>
          </div>

          <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-3">
              <Terminal className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Actionable Anti-Pattern Rules
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
              18+ diagnostic rules highlighting exact causes, remediation code snippets, and web.dev links.
            </p>
          </div>

          <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-3">
              <Shield className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Security & SSRF Guard
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
              Rigorous DNS rebinding protection, HSTS, CSP audit, cookie security verification, and mixed content scans.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full py-6 px-4 border-t border-slate-200 dark:border-slate-800/80 text-center text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between max-w-5xl mx-auto gap-3">
        <span>PageLens © 2026. Automated rate limit: 10 requests / minute / IP.</span>
        <div className="flex items-center gap-4">
          <a
            href="https://github.com/titarek/pagelens"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-slate-300 transition flex items-center gap-1 font-medium"
          >
            <span>GitHub Repository</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </footer>
    </div>
  );
};
