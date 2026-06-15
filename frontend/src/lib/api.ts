// Use the Next.js rewrite proxy to avoid browser Mixed Content errors (HTTPS -> HTTP)
const API_BASE_URL = "/api/proxy";

export interface ResearchRequest {
  topic: string;
  style: string;
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
