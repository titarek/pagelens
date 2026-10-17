import React, { useState, useEffect, useRef } from 'react';
import { Search, Zap, Cpu, ArrowRight, Clipboard, AlertCircle } from 'lucide-react';
import { AnalysisMode } from '../lib/types';

interface UrlInputProps {
  onAnalyze: (url: string, mode: AnalysisMode) => void;
  isLoading: boolean;
  initialUrl?: string;
  initialMode?: AnalysisMode;
  error?: string | null;
}

export const UrlInput: React.FC<UrlInputProps> = ({
  onAnalyze,
  isLoading,
  initialUrl = '',
  initialMode = 'static',
  error = null,
}) => {
  const [url, setUrl] = useState(initialUrl);
  const [mode, setMode] = useState<AnalysisMode>(initialMode);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus();
  }, []);

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text.trim());
        setLocalError(null);
      }
    } catch {
      // Clipboard permissions denied
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    const trimmed = url.trim();
    if (!trimmed) {
      setLocalError('Please enter a target URL to audit.');
      inputRef.current?.focus();
      return;
    }

    let finalUrl = trimmed;
    if (!finalUrl.startsWith('http://') && !finalUrl.startsWith('https://')) {
      finalUrl = 'https://' + finalUrl;
      setUrl(finalUrl);
    }

    try {
      new URL(finalUrl);
    } catch {
      setLocalError('Invalid URL structure. Please enter a valid website address.');
      return;
    }

    onAnalyze(finalUrl, mode);
  };

  const displayError = localError || error;

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        {/* URL Input Box */}
        <div className="relative flex items-center glass-panel rounded-2xl p-2 border border-slate-700/60 focus-within:border-brand-500 shadow-xl transition-all">
          <div className="pl-3 pr-2 text-slate-400">
            <Search className="w-5 h-5" />
          </div>

          <input
            ref={inputRef}
            type="text"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              if (localError) setLocalError(null);
            }}
            placeholder="https://example.com"
            disabled={isLoading}
            className="flex-1 bg-transparent px-2 py-3 text-slate-100 placeholder:text-slate-500 text-base md:text-lg focus:outline-none font-mono"
            aria-label="Target URL"
          />

          {/* Quick Paste Button */}
          {!url && (
            <button
              type="button"
              onClick={handlePaste}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition"
              title="Paste from clipboard"
            >
              <Clipboard className="w-3.5 h-3.5" />
              <span>Paste</span>
            </button>
          )}

          {/* Analyze Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="ml-2 flex items-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-brand-500/20"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span className="hidden sm:inline">Auditing...</span>
              </>
            ) : (
              <>
                <span>Analyze</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>

        {/* Mode Toggle Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-2 text-xs">
          <div className="flex items-center bg-slate-900/80 p-1 rounded-xl border border-slate-800">
            <button
              type="button"
              onClick={() => setMode('static')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                mode === 'static'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Quick Mode (Static)</span>
            </button>

            <button
              type="button"
              onClick={() => setMode('full')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                mode === 'full'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>Deep Mode (Full Render)</span>
            </button>
          </div>

          <span className="text-[11px] text-slate-500 hidden sm:inline">
            {mode === 'static'
              ? 'Sub-second fetch: HTML, CSS & headers'
              : 'Throttled Slow 4G + mobile Playwright Chromium'}
          </span>
        </div>

        {/* Error Display */}
        {displayError && (
          <div className="flex items-center gap-2 p-3 mt-1 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs animate-in fade-in duration-200">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{displayError}</span>
          </div>
        )}
      </form>
    </div>
  );
};
