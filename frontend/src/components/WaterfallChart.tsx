import React, { useState } from 'react';
import { ResourceEntry } from '../lib/types';

interface WaterfallChartProps {
  resources: ResourceEntry[];
}

export const WaterfallChart: React.FC<WaterfallChartProps> = ({ resources }) => {
  const [typeFilter, setTypeFilter] = useState<string>('all');

  const filtered = resources.filter((r) => {
    if (typeFilter === 'all') return true;
    return r.type.toLowerCase() === typeFilter.toLowerCase();
  });

  // Calculate timeline bounds
  const maxEnd = Math.max(
    ...resources.map((r) => (r.start_time_ms || 0) + (r.duration_ms || 10)),
    500
  );

  const typeColors: Record<string, string> = {
    document: 'bg-indigo-500',
    stylesheet: 'bg-sky-400',
    css: 'bg-sky-400',
    script: 'bg-amber-400',
    image: 'bg-pink-400',
    img: 'bg-pink-400',
    font: 'bg-purple-400',
    xhr: 'bg-emerald-400',
    fetch: 'bg-emerald-400',
    other: 'bg-slate-400',
  };

  const getCleanName = (url: string): string => {
    try {
      const parsed = new URL(url);
      const pathname = parsed.pathname;
      const parts = pathname.split('/').filter(Boolean);
      return parts.length > 0 ? parts[parts.length - 1] : parsed.hostname;
    } catch {
      return url.slice(-30);
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col gap-4">
      {/* Header & Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
            Resource Waterfall Timeline
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Network request execution sequence and transfer durations
          </p>
        </div>

        {/* Filter buttons */}
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl text-xs">
          {['all', 'document', 'script', 'stylesheet', 'image', 'font'].map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setTypeFilter(type)}
              className={`px-2.5 py-1 rounded-lg font-medium capitalize transition ${
                typeFilter === type
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Legend & Timeline Scale */}
      <div className="flex items-center justify-between text-xs text-slate-700 dark:text-slate-300 font-mono font-bold px-2">
        <span>0 ms</span>
        <span>{Math.round(maxEnd / 2)} ms</span>
        <span>{Math.round(maxEnd)} ms</span>
      </div>

      {/* Waterfall Rows */}
      {filtered.length === 0 ? (
        <div className="p-8 text-center text-xs text-slate-500">
          No resources matched the selected filter.
        </div>
      ) : (
        <div className="flex flex-col gap-2 max-h-[520px] overflow-y-auto pr-1">
          {filtered.map((item, index) => {
            const startPct = Math.min(100, Math.max(0, (item.start_time_ms / maxEnd) * 100));
            const durationPct = Math.min(
              100 - startPct,
              Math.max(1.5, (item.duration_ms / maxEnd) * 100)
            );
            const colorClass = typeColors[item.type.toLowerCase()] || typeColors.other;
            const sizeKb = (item.size_bytes / 1024).toFixed(1);
            const fileName = getCleanName(item.url);

            return (
              <div
                key={`${item.url}-${index}`}
                className="group flex flex-col sm:flex-row sm:items-center gap-2 p-2 rounded-lg hover:bg-slate-800/40 transition text-xs"
              >
                {/* Resource Info */}
                <div className="w-full sm:w-64 shrink-0 flex items-center justify-between sm:justify-start gap-2 overflow-hidden">
                  <span
                    className="font-mono font-medium truncate text-slate-900 dark:text-slate-100 group-hover:text-brand-400 dark:group-hover:text-white"
                    title={item.url}
                  >
                    {fileName}
                  </span>
                  <span className="shrink-0 text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-bold">
                    {item.type}
                  </span>
                </div>

                {/* Bar Container */}
                <div className="flex-1 relative h-6 bg-slate-200 dark:bg-slate-900/60 rounded overflow-hidden flex items-center">
                  <div
                    className={`absolute h-4 rounded transition-all duration-300 ${colorClass} opacity-90 group-hover:opacity-100 shadow-sm`}
                    style={{
                      left: `${startPct}%`,
                      width: `${durationPct}%`,
                      minWidth: '6px',
                    }}
                    title={`${item.url}\nStart: ${item.start_time_ms}ms\nDuration: ${item.duration_ms}ms\nSize: ${sizeKb} KB`}
                  />
                </div>

                {/* Numeric timing & size */}
                <div className="w-32 shrink-0 flex items-center justify-end gap-3 text-xs font-mono text-slate-700 dark:text-slate-300 font-semibold">
                  <span>{sizeKb} KB</span>
                  <span className="text-slate-950 dark:text-white font-bold">{Math.round(item.duration_ms)} ms</span>
                </div>
              </div>
            );
          })}

        </div>
      )}
    </div>
  );
};
