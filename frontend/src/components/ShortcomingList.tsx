import React, { useState } from 'react';
import { ChevronDown, AlertTriangle, AlertCircle, Info, ExternalLink, CheckCircle } from 'lucide-react';
import { Shortcoming } from '../lib/types';

interface ShortcomingListProps {
  shortcomings: Shortcoming[];
}

export const ShortcomingList: React.FC<ShortcomingListProps> = ({ shortcomings }) => {
  const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set([shortcomings[0]?.id || '']));

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const filteredShortcomings = shortcomings.filter((s) => {
    if (filter === 'all') return true;
    return s.severity === filter;
  });

  const countBySeverity = {
    high: shortcomings.filter((s) => s.severity === 'high').length,
    medium: shortcomings.filter((s) => s.severity === 'medium').length,
    low: shortcomings.filter((s) => s.severity === 'low').length,
  };

  const severityBadges = {
    high: {
      badge: 'bg-rose-500/10 text-rose-500 dark:text-rose-400 border-rose-500/20',
      icon: AlertCircle,
      label: 'High Severity',
    },
    medium: {
      badge: 'bg-amber-500/10 text-amber-500 dark:text-amber-400 border-amber-500/20',
      icon: AlertTriangle,
      label: 'Medium Severity',
    },
    low: {
      badge: 'bg-blue-500/10 text-blue-500 dark:text-blue-400 border-blue-500/20',
      icon: Info,
      label: 'Low Severity',
    },
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-3">
        <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              filter === 'all'
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            All Issues ({shortcomings.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('high')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              filter === 'high'
                ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400 shadow-sm'
                : 'text-slate-500 hover:text-rose-500'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            High ({countBySeverity.high})
          </button>
          <button
            type="button"
            onClick={() => setFilter('medium')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              filter === 'medium'
                ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400 shadow-sm'
                : 'text-slate-500 hover:text-amber-500'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            Medium ({countBySeverity.medium})
          </button>
          <button
            type="button"
            onClick={() => setFilter('low')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              filter === 'low'
                ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-slate-500 hover:text-blue-500'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            Low ({countBySeverity.low})
          </button>
        </div>

        <span className="text-xs text-slate-500 dark:text-slate-400">
          Showing {filteredShortcomings.length} of {shortcomings.length} detected shortcomings
        </span>
      </div>

      {/* Issues List */}
      {filteredShortcomings.length === 0 ? (
        <div className="glass-panel p-10 rounded-2xl text-center border border-slate-200 dark:border-slate-800">
          <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-900 dark:text-white">
            No shortcomings found
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            No performance anti-patterns detected under this severity filter.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {filteredShortcomings.map((item) => {
            const isExpanded = expandedIds.has(item.id);
            const badgeMeta = severityBadges[item.severity];
            const BadgeIcon = badgeMeta.icon;

            return (
              <div
                key={item.id}
                className="glass-panel rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden transition-all duration-200 shadow-sm"
              >
                {/* Header / Trigger */}
                <button
                  type="button"
                  onClick={() => toggleExpand(item.id)}
                  className="w-full p-4 flex items-center justify-between gap-4 text-left hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition"
                  aria-expanded={isExpanded}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${badgeMeta.badge}`}
                    >
                      <BadgeIcon className="w-3.5 h-3.5" />
                      {item.severity.toUpperCase()}
                    </span>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {item.title}
                    </h4>
                  </div>

                  <ChevronDown
                    className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${
                      isExpanded ? 'rotate-180' : ''
                    }`}
                  />
                </button>

                {/* Accordion Content */}
                {isExpanded && (
                  <div className="p-4 pt-0 border-t border-slate-100 dark:border-slate-800/80 bg-slate-50/30 dark:bg-slate-900/20 text-xs flex flex-col gap-3">
                    {/* Cause */}
                    <div>
                      <span className="font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[10px]">
                        Why this is a problem
                      </span>
                      <p className="mt-1 text-slate-600 dark:text-slate-400 leading-relaxed">
                        {item.cause}
                      </p>
                    </div>

                    {/* Fix */}
                    <div>
                      <span className="font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider text-[10px]">
                        Recommended Fix
                      </span>
                      <p className="mt-1 text-slate-600 dark:text-slate-300 font-medium leading-relaxed">
                        {item.fix}
                      </p>
                    </div>

                    {/* Example Code */}
                    {item.example && (
                      <div>
                        <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px]">
                          Example Implementation
                        </span>
                        <pre className="mt-1.5 p-3 rounded-lg bg-slate-900 text-slate-200 font-mono text-[11px] overflow-x-auto border border-slate-800 leading-normal">
                          <code>{item.example}</code>
                        </pre>
                      </div>
                    )}

                    {/* Reference Link */}
                    {item.reference && (
                      <div className="pt-1 flex items-center justify-end">
                        <a
                          href={item.reference}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-brand-600 dark:text-brand-400 hover:underline"
                        >
                          <span>Read web.dev / MDN Documentation</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
