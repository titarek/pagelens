import React, { useState } from 'react';
import { FileCode, FileText, Download, Copy, Check, Search, ExternalLink } from 'lucide-react';
import { getSourceDownloadUrl } from '../lib/api';

interface ScrapedSourceViewerProps {
  jobId: string;
  htmlContent: string;
  cssContent: string;
  htmlBytes?: number;
  cssBytes?: number;
}

export const ScrapedSourceViewer: React.FC<ScrapedSourceViewerProps> = ({
  jobId,
  htmlContent,
  cssContent,
  htmlBytes = 0,
  cssBytes = 0,
}) => {
  const [activeTab, setActiveTab] = useState<'html' | 'css'>('html');
  const [copied, setCopied] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const currentContent = activeTab === 'html' ? htmlContent : cssContent;
  const currentBytes = activeTab === 'html' ? (htmlBytes || htmlContent.length) : (cssBytes || cssContent.length);
  const currentKb = (currentBytes / 1024).toFixed(1);

  const handleCopy = () => {
    navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Split lines for line numbers
  const lines = currentContent.split('\n');
  const lineCount = lines.length;

  // Filter or highlight lines if search term provided
  const filteredIndices = searchTerm
    ? lines
        .map((line, idx) => (line.toLowerCase().includes(searchTerm.toLowerCase()) ? idx : -1))
        .filter((idx) => idx !== -1)
    : null;

  return (
    <div className="glass-panel rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col">
      {/* Header Bar */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4 bg-slate-100/50 dark:bg-slate-900/50">
        {/* Source Type Selector */}
        <div className="flex items-center gap-2 bg-slate-200 dark:bg-slate-800 p-1 rounded-xl text-xs">
          <button
            type="button"
            onClick={() => {
              setActiveTab('html');
              setSearchTerm('');
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition ${
              activeTab === 'html'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-cyan-400" />
            <span>Scraped HTML</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab('css');
              setSearchTerm('');
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition ${
              activeTab === 'css'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-200'
            }`}
          >
            <FileCode className="w-3.5 h-3.5 text-amber-400" />
            <span>Aggregated CSS</span>
          </button>
        </div>

        {/* Stats Pills */}
        <div className="flex items-center gap-3 text-xs font-mono text-slate-500 dark:text-slate-400">
          <span>
            Size: <strong className="text-slate-900 dark:text-slate-200">{currentKb} KB</strong>
          </span>
          <span>•</span>
          <span>
            Lines: <strong className="text-slate-900 dark:text-slate-200">{lineCount}</strong>
          </span>
        </div>

        {/* Action Buttons: Search, Copy & Download */}
        <div className="flex items-center gap-2">
          {/* Quick Filter Search */}
          <div className="relative flex items-center">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search code..."
              className="pl-8 pr-3 py-1.5 text-xs bg-slate-100 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-brand-500 font-mono w-32 sm:w-44"
            />
          </div>

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
            title="Copy source code to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>

          {/* Download File */}
          <a
            href={getSourceDownloadUrl(jobId, activeTab)}
            download
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white transition shadow-sm"
            title={`Download raw .${activeTab} file`}
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download .{activeTab}</span>
          </a>
        </div>
      </div>

      {/* Code Display Area */}
      <div className="relative max-h-[620px] overflow-auto bg-slate-950 text-slate-200 font-mono text-[12px] leading-relaxed p-4 select-text">
        {!currentContent ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No {activeTab.toUpperCase()} content captured for this URL.
          </div>
        ) : (
          <pre className="flex flex-col m-0 overflow-visible font-mono">
            {lines.map((line, idx) => {
              const lineNum = idx + 1;
              const isMatch = filteredIndices ? filteredIndices.includes(idx) : false;
              if (searchTerm && !isMatch) return null;

              return (
                <div
                  key={lineNum}
                  className={`flex items-start hover:bg-slate-900/60 px-1 rounded transition-colors ${
                    isMatch ? 'bg-amber-500/15' : ''
                  }`}
                >
                  <span className="w-12 shrink-0 select-none text-slate-600 text-right pr-4 text-[11px]">
                    {lineNum}
                  </span>
                  <code className="text-slate-300 whitespace-pre-wrap break-all flex-1 font-mono">
                    {line || '\n'}
                  </code>
                </div>
              );
            })}
          </pre>
        )}
      </div>

      {/* Footer Banner */}
      <div className="p-3 bg-slate-900 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
        <span>
          PageLens sanitized source view — raw HTML and CSS are securely rendered as text to prevent arbitrary script execution.
        </span>
        <a
          href={getSourceDownloadUrl(jobId, activeTab)}
          download
          className="text-brand-400 hover:underline flex items-center gap-1 font-medium"
        >
          <span>Direct Raw Download</span>
          <Download className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
};
