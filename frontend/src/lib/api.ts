import {
  AnalyzeRequest,
  AnalyzeResponse,
  Report,
  JobProgressResponse,
  RecentAnalysis,
  InteractionRequest,
  InteractionResult,
} from './types';


const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function submitAnalysis(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE}/api/v1/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(req),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data?.detail || `Failed to submit analysis (${response.status})`;
    throw new ApiError(errorMsg, response.status, data);
  }

  return data as AnalyzeResponse;
}

export async function fetchReport(jobId: string): Promise<Report | JobProgressResponse> {
  const response = await fetch(`${API_BASE}/api/v1/report/${jobId}`);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data?.detail || `Failed to fetch report (${response.status})`;
    throw new ApiError(errorMsg, response.status, data);
  }

  return data;
}

export function getExportUrl(jobId: string, format: 'json' | 'pdf'): string {
  return `${API_BASE}/api/v1/report/${jobId}/export?format=${format}`;
}

export function getSourceDownloadUrl(jobId: string, type: 'html' | 'css'): string {
  return `${API_BASE}/api/v1/report/${jobId}/source/download?type=${type}`;
}

export async function fetchScrapedSource(jobId: string) {
  const response = await fetch(`${API_BASE}/api/v1/report/${jobId}/source`);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data?.detail || `Failed to fetch source (${response.status})`;
    throw new ApiError(errorMsg, response.status, data);
  }

  return data;
}

export async function simulateInteraction(req: InteractionRequest): Promise<InteractionResult> {
  const response = await fetch(`${API_BASE}/api/v1/analyze/interact`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(req),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data?.detail || `Failed to simulate interaction (${response.status})`;
    throw new ApiError(errorMsg, response.status, data);
  }

  return data as InteractionResult;
}


const RECENT_KEY = 'pagelens_recent_analyses';

export function getRecentAnalyses(): RecentAnalysis[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveRecentAnalysis(item: RecentAnalysis): void {
  try {
    const existing = getRecentAnalyses().filter((x) => x.job_id !== item.job_id);
    const updated = [item, ...existing].slice(0, 10);
    localStorage.setItem(RECENT_KEY, JSON.stringify(updated));
  } catch {
    // Ignore storage quota errors
  }
}
