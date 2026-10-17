import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, ShieldX, Check, AlertTriangle, X } from 'lucide-react';
import { SecurityAudit } from '../lib/types';

interface SecurityPanelProps {
  security: SecurityAudit;
}

export const SecurityPanel: React.FC<SecurityPanelProps> = ({ security }) => {
  const [filter, setFilter] = useState<'all' | 'pass' | 'warn' | 'fail'>('all');

  const filteredChecks = security.checks.filter((c) => {
    if (filter === 'all') return true;
    return c.status === filter;
  });

  const statusIcons = {
    pass: <Check className="w-4 h-4 text-emerald-500" />,
    warn: <AlertTriangle className="w-4 h-4 text-amber-500" />,
    fail: <X className="w-4 h-4 text-rose-500" />,
  };

  const statusBadges = {
    pass: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    warn: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    fail: 'bg-rose-500/10 text-rose-500 border-rose-500/20',
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Security Score Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-6 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-500">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">
              Security & Header Hygiene Score
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Evaluates HTTPS enforcement, HSTS, CSP, MIME-sniffing, framing, cookies, and library vulnerabilities.
            </p>
          </div>
        </div>

        {/* Counters */}
        <div className="flex items-center gap-3">
          <div className="px-3.5 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
            <span className="block text-lg font-mono font-bold text-emerald-500">
              {security.passed}
            </span>
            <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
              Passed
            </span>
          </div>

          <div className="px-3.5 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-center">
            <span className="block text-lg font-mono font-bold text-amber-500">
              {security.warnings}
            </span>
            <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
              Warnings
            </span>
          </div>

          <div className="px-3.5 py-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-center">
            <span className="block text-lg font-mono font-bold text-rose-500">
              {security.failures}
            </span>
            <span className="text-[10px] font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider">
              Failures
            </span>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
        <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              filter === 'all'
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-200'
            }`}
          >
            All Checks ({security.checks.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('pass')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              filter === 'pass'
                ? 'bg-emerald-500/20 text-emerald-500 shadow-sm'
                : 'text-slate-500 hover:text-emerald-500'
            }`}
          >
            Passed ({security.passed})
          </button>
          <button
            type="button"
            onClick={() => setFilter('warn')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              filter === 'warn'
                ? 'bg-amber-500/20 text-amber-500 shadow-sm'
                : 'text-slate-500 hover:text-amber-500'
            }`}
          >
            Warnings ({security.warnings})
          </button>
          <button
            type="button"
            onClick={() => setFilter('fail')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              filter === 'fail'
                ? 'bg-rose-500/20 text-rose-500 shadow-sm'
                : 'text-slate-500 hover:text-rose-500'
            }`}
          >
            Failures ({security.failures})
          </button>
        </div>
      </div>

      {/* Security Checks Table / Cards */}
      <div className="flex flex-col gap-3">
        {filteredChecks.map((check) => (
          <div
            key={check.id}
            className="glass-panel p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition shadow-sm"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5 shrink-0">{statusIcons[check.status]}</div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {check.title}
                  </h4>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                      statusBadges[check.status]
                    }`}
                  >
                    {check.status.toUpperCase()}
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
                  {check.detail}
                </p>
                {check.status !== 'pass' && (
                  <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-1.5 font-medium">
                    <span className="font-semibold uppercase tracking-wider text-[10px]">Fix: </span>
                    {check.fix}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
