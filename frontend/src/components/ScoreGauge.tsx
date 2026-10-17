import React from 'react';

interface ScoreGaugeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  showBreakdown?: boolean;
}

export const getScoreColor = (score: number): { hex: string; textClass: string; bgClass: string; ringClass: string } => {
  if (score >= 80) {
    return {
      hex: '#22c55e',
      textClass: 'text-emerald-500 dark:text-emerald-400',
      bgClass: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
      ringClass: 'stroke-emerald-500',
    };
  }
  if (score >= 50) {
    return {
      hex: '#f59e0b',
      textClass: 'text-amber-500 dark:text-amber-400',
      bgClass: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
      ringClass: 'stroke-amber-500',
    };
  }
  return {
    hex: '#ef4444',
    textClass: 'text-rose-500 dark:text-rose-400',
    bgClass: 'bg-rose-500/10 text-rose-500 border-rose-500/20',
    ringClass: 'stroke-rose-500',
  };
};

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  score,
  size = 'md',
  label = 'Performance Score',
  showBreakdown = false,
}) => {
  const safeScore = Math.max(0, Math.min(100, Math.round(score)));
  const { hex, textClass, ringClass } = getScoreColor(safeScore);

  const dimensions = {
    sm: { sizePx: 56, strokeWidth: 5, fontSize: 'text-sm', labelSize: 'text-[9px]' },
    md: { sizePx: 120, strokeWidth: 9, fontSize: 'text-3xl', labelSize: 'text-xs' },
    lg: { sizePx: 180, strokeWidth: 12, fontSize: 'text-5xl', labelSize: 'text-sm' },
  }[size];

  const radius = (dimensions.sizePx - dimensions.strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (safeScore / 100) * circumference;

  return (
    <div
      className="flex flex-col items-center justify-center relative select-none"
      role="meter"
      aria-label={label}
      aria-valuenow={safeScore}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="relative flex items-center justify-center">
        <svg
          width={dimensions.sizePx}
          height={dimensions.sizePx}
          className="transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={dimensions.sizePx / 2}
            cy={dimensions.sizePx / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={dimensions.strokeWidth}
            className="text-slate-200 dark:text-slate-800"
            fill="transparent"
          />
          {/* Foreground progress circle */}
          <circle
            cx={dimensions.sizePx / 2}
            cy={dimensions.sizePx / 2}
            r={radius}
            strokeWidth={dimensions.strokeWidth}
            strokeLinecap="round"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={`${ringClass} transition-all duration-700 ease-out`}
          />
        </svg>

        {/* Center score readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`font-mono font-bold tracking-tight ${dimensions.fontSize} ${textClass}`}>
            {safeScore}
          </span>
          {size !== 'sm' && (
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
              / 100
            </span>
          )}
        </div>
      </div>

      {label && size !== 'sm' && (
        <span className={`mt-2 font-medium text-slate-600 dark:text-slate-400 ${dimensions.labelSize}`}>
          {label}
        </span>
      )}
    </div>
  );
};
