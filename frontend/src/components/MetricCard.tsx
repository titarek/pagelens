import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  status?: 'good' | 'warn' | 'bad' | 'neutral';
  benchmark?: string;
  description?: string;
  icon?: LucideIcon;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  status = 'neutral',
  benchmark,
  description,
  icon: Icon,
}) => {
  const statusStyles = {
    good: {
      badge: 'bg-emerald-500/10 text-emerald-500 dark:text-emerald-400 border-emerald-500/20',
      dot: 'bg-emerald-500',
      border: 'hover:border-emerald-500/30',
    },
    warn: {
      badge: 'bg-amber-500/10 text-amber-500 dark:text-amber-400 border-amber-500/20',
      dot: 'bg-amber-500',
      border: 'hover:border-amber-500/30',
    },
    bad: {
      badge: 'bg-rose-500/10 text-rose-500 dark:text-rose-400 border-rose-500/20',
      dot: 'bg-rose-500',
      border: 'hover:border-rose-500/30',
    },
    neutral: {
      badge: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
      dot: 'bg-slate-400',
      border: 'hover:border-slate-500/30',
    },
  }[status];

  return (
    <div
      className={`glass-panel p-5 rounded-xl border border-slate-200 dark:border-slate-800 transition-all duration-200 shadow-sm hover:shadow-md ${statusStyles.border}`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {title}
        </span>
        {Icon && <Icon className="w-4 h-4 text-slate-400" />}
      </div>

      <div className="flex items-baseline gap-1 my-1">
        <span className="text-2xl lg:text-3xl font-mono font-bold tracking-tight text-slate-900 dark:text-white">
          {value}
        </span>
        {unit && (
          <span className="text-sm font-medium text-slate-500 dark:text-slate-400 font-mono">
            {unit}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-xs">
        {benchmark ? (
          <span className="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
            Goal: {benchmark}
          </span>
        ) : (
          <span />
        )}

        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${statusStyles.badge}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${statusStyles.dot}`} />
          {status.toUpperCase()}
        </span>
      </div>

      {description && (
        <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
          {description}
        </p>
      )}
    </div>
  );
};
