import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LabelList,
} from 'recharts';
import { StructuralMetrics } from '../lib/types';

interface ResourceBreakdownProps {
  structural: StructuralMetrics;
}

const COLORS = ['#6366f1', '#38bdf8', '#f59e0b', '#ec4899', '#8b5cf6', '#64748b'];

export const ResourceBreakdown: React.FC<ResourceBreakdownProps> = ({ structural }) => {
  const byteData = [
    { name: 'HTML', value: Math.round(structural.html_bytes / 1024), rawBytes: structural.html_bytes, color: '#6366f1' },
    { name: 'CSS', value: Math.round(structural.css_bytes / 1024), rawBytes: structural.css_bytes, color: '#38bdf8' },
    { name: 'JavaScript', value: Math.round(structural.js_bytes / 1024), rawBytes: structural.js_bytes, color: '#f59e0b' },
    { name: 'Images', value: Math.round(structural.image_bytes / 1024), rawBytes: structural.image_bytes, color: '#ec4899' },
    { name: 'Fonts', value: Math.round(structural.font_bytes / 1024), rawBytes: structural.font_bytes, color: '#8b5cf6' },
  ].filter((item) => item.value > 0);

  const countData = [
    { name: 'Stylesheets', count: structural.num_stylesheets, fill: '#38bdf8' },
    { name: 'Scripts', count: structural.num_scripts, fill: '#f59e0b' },
    { name: 'Images', count: structural.num_images, fill: '#ec4899' },
    { name: 'Fonts', count: structural.num_fonts, fill: '#8b5cf6' },
  ];

  const totalKb = Math.round(structural.total_bytes / 1024);

  return (
    <div className="flex flex-col gap-6">
      {/* Visual Chart Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Donut Chart: Byte Distribution */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
              Payload Weight Distribution
            </h4>
            <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-200 bg-slate-200 dark:bg-slate-800 px-2 py-0.5 rounded-md">
              Total: {totalKb} KB
            </span>
          </div>

          <div className="w-full h-64 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={byteData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {byteData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: number) => [`${val} KB`, 'Weight']}
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#475569',
                    borderRadius: '0.75rem',
                    color: '#f8fafc',
                    fontSize: '13px',
                    fontWeight: '600',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
                  }}
                  itemStyle={{ color: '#38bdf8', fontWeight: 'bold' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            {byteData.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5 text-xs text-slate-700 dark:text-slate-300 font-medium">
                <span className="w-2.5 h-2.5 rounded-full shadow-sm" style={{ backgroundColor: item.color }} />
                <span>{item.name}:</span>
                <span className="font-mono font-bold text-slate-900 dark:text-white">{item.value} KB</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bar Chart: Request Counts */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
              Asset Counts by Type
            </h4>
            <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-200 bg-slate-200 dark:bg-slate-800 px-2 py-0.5 rounded-md">
              Total Requests: {structural.num_requests}
            </span>
          </div>

          <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={countData} margin={{ top: 20, right: 15, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                <XAxis
                  dataKey="name"
                  stroke="#94a3b8"
                  tick={{ fill: '#e2e8f0', fontSize: 12, fontWeight: 600 }}
                  tickLine={{ stroke: '#64748b' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  tick={{ fill: '#e2e8f0', fontSize: 12, fontWeight: 600 }}
                  tickLine={{ stroke: '#64748b' }}
                />
                <Tooltip
                  formatter={(val: number) => [val, 'Count']}
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#475569',
                    borderRadius: '0.75rem',
                    color: '#f8fafc',
                    fontSize: '13px',
                    fontWeight: '600',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
                  }}
                  itemStyle={{ color: '#818cf8', fontWeight: 'bold' }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} fill="#6366f1">
                  <LabelList
                    dataKey="count"
                    position="top"
                    fill="#f1f5f9"
                    fontSize={13}
                    fontWeight={700}
                    offset={8}
                  />
                  {countData.map((entry, index) => (
                    <Cell key={`bar-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300 font-medium flex items-center justify-between">
            <span>Blocking Scripts: <strong className="text-rose-400 font-bold">{structural.num_blocking_scripts}</strong></span>
            <span>Total DOM Elements: <strong className="text-slate-900 dark:text-white font-bold">{structural.num_dom_elements}</strong></span>
          </div>
        </div>
      </div>


      {/* Structured Metrics Table */}
      <div className="glass-panel rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
            Delivery & Compression Diagnostics
          </h4>
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
          <div className="p-3.5 flex items-center justify-between">
            <span className="text-slate-600 dark:text-slate-400">HTTP Content Compression</span>
            <span className="font-mono font-semibold uppercase px-2 py-0.5 rounded bg-slate-800 text-brand-300">
              {structural.compression_used}
            </span>
          </div>
          <div className="p-3.5 flex items-center justify-between">
            <span className="text-slate-600 dark:text-slate-400">HTML Minification</span>
            <span className={`font-semibold ${structural.minified_html ? 'text-emerald-400' : 'text-amber-400'}`}>
              {structural.minified_html ? 'Minified' : 'Unminified (whitespace/comments)'}
            </span>
          </div>
          <div className="p-3.5 flex items-center justify-between">
            <span className="text-slate-600 dark:text-slate-400">CSS Minification</span>
            <span className={`font-semibold ${structural.minified_css ? 'text-emerald-400' : 'text-amber-400'}`}>
              {structural.minified_css ? 'Minified' : 'Unminified'}
            </span>
          </div>
          <div className="p-3.5 flex items-center justify-between">
            <span className="text-slate-600 dark:text-slate-400">Text to HTML Ratio</span>
            <span className="font-mono font-semibold text-slate-900 dark:text-slate-200">
              {(structural.text_to_html_ratio * 100).toFixed(1)}%
            </span>
          </div>
          <div className="p-3.5 flex items-center justify-between">
            <span className="text-slate-600 dark:text-slate-400">Inline CSS Ratio</span>
            <span className="font-mono font-semibold text-slate-900 dark:text-slate-200">
              {(structural.inline_css_ratio * 100).toFixed(1)}%
            </span>
          </div>
          <div className="p-3.5 flex items-center justify-between">
            <span className="text-slate-600 dark:text-slate-400">Images Over 200 KB Budget</span>
            <span className={`font-mono font-semibold ${structural.images_over_200kb > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {structural.images_over_200kb}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
