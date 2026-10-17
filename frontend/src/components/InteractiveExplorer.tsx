import React, { useState } from 'react';
import {
  MousePointerClick,
  Compass,
  Link as LinkIcon,
  ListFilter,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  Search,
  ExternalLink,
  Activity,
  ArrowRight,
  Code,
  FileCode,
  FileText,
  Layers,
  Terminal,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
  Cell,
} from 'recharts';
import {
  DiscoveredOptionsSummary,
  DiscoveredOption,
  InteractionResult,
  InteractionRequest,
} from '../lib/types';
import { simulateInteraction } from '../lib/api';

interface InteractiveExplorerProps {
  baseUrl: string;
  discoveredOptions?: DiscoveredOptionsSummary | null;
  onAuditRoute?: (url: string) => void;
}

export const InteractiveExplorer: React.FC<InteractiveExplorerProps> = ({
  baseUrl,
  discoveredOptions,
  onAuditRoute,
}) => {
  const [filterType, setFilterType] = useState<'all' | 'link' | 'select_option' | 'button' | 'form'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form custom simulation state
  const [actionType, setActionType] = useState<'click' | 'select' | 'navigate'>('click');
  const [targetSelector, setTargetSelector] = useState('');
  const [actionValue, setActionValue] = useState('');
  const [targetUrl, setTargetUrl] = useState('');

  // Result state
  const [result, setResult] = useState<InteractionResult | null>(null);
  const [codeTab, setCodeTab] = useState<'html' | 'css'>('html');
  const [copiedCode, setCopiedCode] = useState(false);
  const [codeSearch, setCodeSearch] = useState('');

  // Collect all options into a flat array
  const allOptions: DiscoveredOption[] = React.useMemo(() => {
    if (!discoveredOptions) return [];
    const list: DiscoveredOption[] = [];
    if (discoveredOptions.internal_links) list.push(...discoveredOptions.internal_links);
    if (discoveredOptions.select_options) list.push(...discoveredOptions.select_options);
    if (discoveredOptions.buttons) list.push(...discoveredOptions.buttons);
    if (discoveredOptions.forms) list.push(...discoveredOptions.forms);
    return list;
  }, [discoveredOptions]);

  // Filter options based on category and search query
  const filteredOptions = allOptions.filter((opt) => {
    if (filterType !== 'all' && opt.category !== filterType) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const matchLabel = opt.label.toLowerCase().includes(q);
      const matchTarget = opt.target.toLowerCase().includes(q);
      const matchSelector = opt.selector?.toLowerCase().includes(q) || false;
      return matchLabel || matchTarget || matchSelector;
    }
    return true;
  });

  const handleSimulate = async (req: InteractionRequest) => {
    setIsRunning(true);
    setErrorMsg(null);
    try {
      const res = await simulateInteraction(req);
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to simulate interaction.');
    } finally {
      setIsRunning(false);
    }
  };

  const handleSelectOptionFromCatalog = (opt: DiscoveredOption) => {
    if (opt.category === 'link') {
      setActionType('navigate');
      setTargetUrl(opt.target);
      setTargetSelector(opt.selector || '');
      setActionValue('');
    } else if (opt.category === 'select_option') {
      setActionType('select');
      setTargetSelector(opt.selector || '');
      setActionValue(opt.target);
      setTargetUrl('');
    } else if (opt.category === 'button') {
      setActionType('click');
      setTargetSelector(opt.selector || '');
      setActionValue('');
      setTargetUrl('');
    } else if (opt.category === 'form') {
      setActionType('navigate');
      setTargetUrl(opt.target);
      setTargetSelector(opt.selector || '');
      setActionValue('');
    }
  };

  const handleCopyCode = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  // Prepare network chart data with clean labels
  const networkChartData = (result?.network_requests || []).slice(0, 15).map((req, idx) => {
    let cleanLabel = req.url;
    try {
      const u = new URL(req.url);
      const segments = u.pathname.split('/').filter(Boolean);
      cleanLabel = segments.length > 0 ? segments[segments.length - 1] : u.hostname;
    } catch {
      cleanLabel = req.url.slice(-25);
    }
    if (cleanLabel.length > 18) cleanLabel = cleanLabel.slice(0, 16) + '…';

    return {
      name: `#${idx + 1} ${cleanLabel}`,
      duration: Math.round(req.duration_ms),
      sizeKb: parseFloat((req.size_bytes / 1024).toFixed(1)),
      status: req.status,
      type: req.resource_type,
      fullUrl: req.url,
      fill: req.status >= 400 ? '#ef4444' : req.resource_type === 'xhr' || req.resource_type === 'fetch' ? '#10b981' : '#6366f1',
    };
  });

  const activeCodeContent = codeTab === 'html' ? (result?.html_after || '') : (result?.css_after || '');
  const codeLines = activeCodeContent.split('\n');

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-200">
      {/* 1. Header Hero Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-brand-400 font-semibold text-xs uppercase tracking-wider">
            <Compass className="w-4 h-4" />
            <span>Option Discovery & State Simulation</span>
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-1">
            Explore All Possible Options & Simulate Interactions
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-2xl leading-relaxed">
            PageLens automatically discovers all interactive buttons, select dropdown options, forms, and internal navigation routes on the page. Choose an option to simulate user action via headless Chromium and capture the post-interaction DOM mutation, dynamic CSS, and network delta.
          </p>
        </div>

        {/* Discovery Counter Stats */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex flex-col items-center justify-center p-3 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center min-w-[80px]">
            <span className="text-lg font-mono font-bold text-brand-500">
              {discoveredOptions?.total_count || allOptions.length}
            </span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
              Total Options
            </span>
          </div>

          <div className="flex flex-col items-center justify-center p-3 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center min-w-[80px]">
            <span className="text-lg font-mono font-bold text-sky-400">
              {discoveredOptions?.internal_links?.length || 0}
            </span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
              Routes
            </span>
          </div>

          <div className="flex flex-col items-center justify-center p-3 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center min-w-[80px]">
            <span className="text-lg font-mono font-bold text-amber-400">
              {discoveredOptions?.select_options?.length || 0}
            </span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
              Dropdowns
            </span>
          </div>

          <div className="flex flex-col items-center justify-center p-3 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center min-w-[80px]">
            <span className="text-lg font-mono font-bold text-emerald-400">
              {discoveredOptions?.buttons?.length || 0}
            </span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
              Buttons
            </span>
          </div>
        </div>
      </div>

      {/* 2. Interactive Action Simulator Runner Form */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <MousePointerClick className="w-4 h-4 text-brand-400" />
            <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
              Simulate Action on Page
            </h4>
          </div>
          <span className="text-xs text-slate-400">
            Target Page: <strong className="text-slate-200 font-mono">{baseUrl}</strong>
          </span>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSimulate({
              url: baseUrl,
              action_type: actionType,
              selector: targetSelector || undefined,
              value: actionValue || undefined,
              target_url: targetUrl || undefined,
            });
          }}
          className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end"
        >
          {/* Action Type Select */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Interaction Type
            </label>
            <select
              value={actionType}
              onChange={(e) => setActionType(e.target.value as any)}
              className="px-3 py-2 text-xs bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl text-slate-900 dark:text-slate-100 focus:outline-none focus:border-brand-500 font-medium"
            >
              <option value="click">Click Element (Button / Link / Tab)</option>
              <option value="select">Select Option (Dropdown &lt;select&gt;)</option>
              <option value="navigate">Navigate Route (Sub-Page URL)</option>
            </select>
          </div>

          {/* Selector / Target Input */}
          <div className="flex flex-col gap-1.5 md:col-span-2">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              {actionType === 'navigate' ? 'Target Route URL' : 'CSS Selector or Identifier'}
            </label>
            <input
              type="text"
              value={actionType === 'navigate' ? targetUrl : targetSelector}
              onChange={(e) => {
                if (actionType === 'navigate') setTargetUrl(e.target.value);
                else setTargetSelector(e.target.value);
              }}
              placeholder={
                actionType === 'navigate'
                  ? 'https://example.com/pricing'
                  : actionType === 'select'
                  ? 'select#country or select[name="theme"]'
                  : '#login-button or button.submit'
              }
              className="px-3 py-2 text-xs bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-brand-500 font-mono"
            />
          </div>

          {/* Value Input (for Select) or Action Button */}
          {actionType === 'select' ? (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Option Value
              </label>
              <input
                type="text"
                value={actionValue}
                onChange={(e) => setActionValue(e.target.value)}
                placeholder="Option value to select"
                className="px-3 py-2 text-xs bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-brand-500 font-mono"
              />
            </div>
          ) : (
            <div className="flex items-center">
              <button
                type="submit"
                disabled={isRunning}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 text-xs font-bold text-white bg-brand-600 hover:bg-brand-500 disabled:opacity-50 rounded-xl shadow-md transition"
              >
                {isRunning ? (
                  <>
                    <Activity className="w-4 h-4 animate-spin text-white" />
                    <span>Executing in Chromium...</span>
                  </>
                ) : (
                  <>
                    <MousePointerClick className="w-4 h-4" />
                    <span>Simulate & Inspect Result</span>
                  </>
                )}
              </button>
            </div>
          )}

          {actionType === 'select' && (
            <div className="md:col-span-4 flex justify-end">
              <button
                type="submit"
                disabled={isRunning}
                className="flex items-center justify-center gap-2 px-6 py-2 text-xs font-bold text-white bg-brand-600 hover:bg-brand-500 disabled:opacity-50 rounded-xl shadow-md transition"
              >
                {isRunning ? (
                  <>
                    <Activity className="w-4 h-4 animate-spin text-white" />
                    <span>Executing in Chromium...</span>
                  </>
                ) : (
                  <>
                    <MousePointerClick className="w-4 h-4" />
                    <span>Simulate & Inspect Result</span>
                  </>
                )}
              </button>
            </div>
          )}
        </form>

        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* 3. Post-Interaction Results Panel (Displayed once simulation runs) */}
      {result && (
        <div className="glass-panel p-6 rounded-2xl border border-brand-500/40 bg-brand-950/10 shadow-lg flex flex-col gap-6 animate-in slide-in-from-top-4 duration-300">
          {/* Result Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                <h4 className="text-base font-bold text-slate-900 dark:text-white">
                  Simulation Outcome: {result.target_description}
                </h4>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 font-medium">
                {result.summary}
              </p>
            </div>

            <span className="text-xs font-mono font-bold px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200">
              Execution Latency: {result.duration_ms} ms
            </span>
          </div>

          {/* 4 State Delta Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* DOM Mutation */}
            <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 flex flex-col">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                DOM Mutation Delta
              </span>
              <div className="flex items-baseline gap-2 mt-2">
                <span
                  className={`text-2xl font-mono font-bold ${
                    result.dom_delta > 0
                      ? 'text-emerald-400'
                      : result.dom_delta < 0
                      ? 'text-amber-400'
                      : 'text-slate-200'
                  }`}
                >
                  {result.dom_delta > 0 ? `+${result.dom_delta}` : result.dom_delta}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  ({result.dom_elements_before} &rarr; {result.dom_elements_after} nodes)
                </span>
              </div>
            </div>

            {/* Network Requests Triggered */}
            <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 flex flex-col">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Triggered Network Calls
              </span>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-2xl font-mono font-bold text-sky-400">
                  {result.triggered_requests_count}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  ({(result.triggered_requests_bytes / 1024).toFixed(1)} KB transferred)
                </span>
              </div>
            </div>

            {/* HTML Size Delta */}
            <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 flex flex-col">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Post-Action HTML Size
              </span>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-2xl font-mono font-bold text-indigo-400">
                  {(result.html_bytes_after / 1024).toFixed(1)} KB
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  ({result.html_bytes_delta >= 0 ? `+${result.html_bytes_delta}` : result.html_bytes_delta} B)
                </span>
              </div>
            </div>

            {/* Route Status */}
            <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 flex flex-col">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Route Transition
              </span>
              <div className="mt-2 text-xs font-mono font-bold truncate">
                {result.url_changed ? (
                  <span className="text-emerald-400">Navigated to new route</span>
                ) : (
                  <span className="text-slate-300">In-Place State Mutation</span>
                )}
              </div>
              <span className="text-[10px] text-slate-500 truncate mt-1" title={result.final_url}>
                {result.final_url}
              </span>
            </div>
          </div>

          {/* Triggered Network Requests Bar Chart (Ensuring high-contrast, crystal-clear labels) */}
          {networkChartData.length > 0 && (
            <div className="p-5 rounded-xl bg-slate-100 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <h5 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-emerald-400" />
                  Network Requests Triggered by Interaction
                </h5>
                <span className="text-xs font-mono font-semibold text-slate-700 dark:text-slate-200 bg-slate-200 dark:bg-slate-800 px-2 py-0.5 rounded">
                  Showing top {networkChartData.length} requests
                </span>
              </div>

              <div className="w-full h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={networkChartData} margin={{ top: 20, right: 15, left: -10, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#475569" opacity={0.35} />
                    <XAxis
                      dataKey="name"
                      stroke="#94a3b8"
                      tick={{ fill: '#e2e8f0', fontSize: 12, fontWeight: 600 }}
                      tickLine={{ stroke: '#64748b' }}
                      angle={-15}
                      textAnchor="end"
                      height={40}
                    />
                    <YAxis
                      stroke="#94a3b8"
                      tick={{ fill: '#e2e8f0', fontSize: 12, fontWeight: 600 }}
                      tickLine={{ stroke: '#64748b' }}
                      unit="ms"
                    />
                    <Tooltip
                      formatter={(val: number, name: string) => [
                        `${val} ms`,
                        'Latency Duration',
                      ]}
                      contentStyle={{
                        backgroundColor: '#020617',
                        borderColor: '#38bdf8',
                        borderRadius: '0.75rem',
                        color: '#f8fafc',
                        fontSize: '13px',
                        fontWeight: '600',
                        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.6)',
                      }}
                      itemStyle={{ color: '#38bdf8', fontWeight: 'bold' }}
                    />
                    <Bar dataKey="duration" radius={[6, 6, 0, 0]} fill="#38bdf8">
                      <LabelList
                        dataKey="duration"
                        position="top"
                        fill="#f8fafc"
                        fontSize={12}
                        fontWeight={700}
                        offset={6}
                        formatter={(val: number) => `${val}ms`}
                      />
                      {networkChartData.map((entry, index) => (
                        <Cell key={`net-cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Mutated Code Viewer */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col bg-slate-950">
            <div className="p-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-900/60">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCodeTab('html')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    codeTab === 'html'
                      ? 'bg-brand-600 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Mutated HTML State</span>
                </button>
                <button
                  type="button"
                  onClick={() => setCodeTab('css')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    codeTab === 'css'
                      ? 'bg-brand-600 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5 text-amber-400" />
                  <span>Post-Action CSS</span>
                </button>
              </div>

              <div className="flex items-center gap-2">
                <div className="relative flex items-center">
                  <Search className="w-3 h-3 text-slate-500 absolute left-2" />
                  <input
                    type="text"
                    value={codeSearch}
                    onChange={(e) => setCodeSearch(e.target.value)}
                    placeholder="Search mutated DOM..."
                    className="pl-7 pr-2.5 py-1 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder:text-slate-500 font-mono w-40 focus:outline-none focus:border-brand-500"
                  />
                </div>

                <button
                  type="button"
                  onClick={() => handleCopyCode(activeCodeContent)}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
                >
                  {copiedCode ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedCode ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            </div>

            <div className="p-4 max-h-72 overflow-y-auto text-xs font-mono text-slate-300 leading-relaxed select-text">
              <pre className="m-0 whitespace-pre-wrap break-all">
                {codeLines
                  .filter((l) => (codeSearch ? l.toLowerCase().includes(codeSearch.toLowerCase()) : true))
                  .slice(0, 200)
                  .join('\n')}
              </pre>
            </div>
          </div>

          {/* Console Messages (if any) */}
          {result.console_logs && result.console_logs.length > 0 && (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col gap-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-amber-400">
                <Terminal className="w-4 h-4" />
                <span>Client-Side Console Messages Triggered by Action:</span>
              </div>
              <div className="flex flex-col gap-1 text-[11px] font-mono text-slate-400">
                {result.console_logs.map((log, idx) => (
                  <div key={idx} className="truncate">
                    {log}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4. Discovered Options Catalog */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-3">
          <div>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-brand-400" />
              Discovered Options Catalog ({filteredOptions.length})
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Click any discovered element below to auto-fill the simulation form or audit that sub-page.
            </p>
          </div>

          {/* Category Filter Tabs */}
          <div className="flex flex-wrap items-center gap-1 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl text-xs font-medium">
            {[
              { id: 'all', label: `All (${allOptions.length})` },
              { id: 'link', label: `Routes (${discoveredOptions?.internal_links?.length || 0})` },
              { id: 'select_option', label: `Dropdowns (${discoveredOptions?.select_options?.length || 0})` },
              { id: 'button', label: `Buttons (${discoveredOptions?.buttons?.length || 0})` },
              { id: 'form', label: `Forms (${discoveredOptions?.forms?.length || 0})` },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setFilterType(t.id as any)}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filterType === t.id
                    ? 'bg-brand-600 text-white font-semibold shadow-sm'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Search input for options */}
        <div className="relative flex items-center">
          <Search className="w-4 h-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search discovered routes, buttons, dropdown options..."
            className="w-full pl-9 pr-4 py-2 text-xs bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-brand-500 font-medium"
          />
        </div>

        {/* Options Grid */}
        {filteredOptions.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No interactive options found matching your filter criteria.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[500px] overflow-y-auto pr-1">
            {filteredOptions.map((opt, idx) => {
              const isLink = opt.category === 'link';
              const isSelect = opt.category === 'select_option';
              const isButton = opt.category === 'button';
              const isForm = opt.category === 'form';

              return (
                <div
                  key={`${opt.category}-${opt.target}-${idx}`}
                  className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-900/60 hover:border-brand-500/50 hover:bg-slate-100 dark:hover:bg-slate-900 transition flex flex-col justify-between gap-3 group"
                >
                  <div className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-md font-bold ${
                          isLink
                            ? 'bg-sky-500/15 text-sky-400 border border-sky-500/20'
                            : isSelect
                            ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                            : isButton
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                            : 'bg-purple-500/15 text-purple-400 border border-purple-500/20'
                        }`}
                      >
                        {opt.category.replace('_', ' ')}
                      </span>

                      {isLink && (
                        <span className="text-[10px] text-slate-500 font-mono truncate max-w-[120px]">
                          {opt.attributes?.path || '/'}
                        </span>
                      )}
                    </div>

                    <h5
                      className="text-xs font-semibold text-slate-900 dark:text-slate-100 line-clamp-2"
                      title={opt.label}
                    >
                      {opt.label}
                    </h5>

                    <p
                      className="text-[11px] font-mono text-slate-500 dark:text-slate-400 truncate"
                      title={opt.target}
                    >
                      {opt.target}
                    </p>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 pt-2 border-t border-slate-200 dark:border-slate-800/60">
                    <button
                      type="button"
                      onClick={() => handleSelectOptionFromCatalog(opt)}
                      className="flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-brand-600/10 hover:bg-brand-600 text-brand-400 hover:text-white border border-brand-500/20 transition"
                      title="Load this option into the simulator"
                    >
                      <span>Simulate</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>

                    {isLink && onAuditRoute && (
                      <button
                        type="button"
                        onClick={() => onAuditRoute(opt.target)}
                        className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition flex items-center gap-1"
                        title="Run full standalone audit on this sub-page"
                      >
                        <span>Audit</span>
                        <ExternalLink className="w-3 h-3 text-sky-400" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
