// BP-15: Use env var so the deployed Vercel frontend can point to the real backend.
// In local dev: falls back to the Next.js rewrite proxy at /api/proxy.
// In production (Vercel): set NEXT_PUBLIC_API_URL=https://your-backend.com in Vercel dashboard.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/proxy";

export interface ResearchRequest {
  topic: string;
  style: string;
  model?: string;
  skip_memory: boolean;
  session_id: string;
}

export interface JobCreatedResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  topic: string;
  style: string;
  created_at: string;
  updated_at: string;
  result?: any;
  error?: string;
}

export async function submitResearchJob(data: ResearchRequest): Promise<JobCreatedResponse> {
  const response = await fetch(`${API_BASE_URL}/research`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

export async function pollJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/research/${jobId}`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

// BP-02: Cancel a running job on the server (not just the UI polling)
export async function cancelResearchJob(jobId: string): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/research/${jobId}`, { method: "DELETE" });
  } catch {
    // Non-fatal: if cancel fails, server job may still complete but UI is reset
  }
}
