import type {
  CertificateIssueRequest,
  CertificateIssueResponse,
  CertificateMetadata,
  HealthResponse,
  LogsResponse,
  ManualDnsChallengeCompleteRequest,
  ManualDnsChallengeCompleteResponse,
  ManualDnsChallengeStartRequest,
  ManualDnsChallengeStartResponse,
  NginxAutomationRequest,
  NginxAutomationResponse,
  NginxConfigSnapshot,
  RenewalRunResponse,
  RenewalStatusResponse,
  SystemStatusResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_NORTHSSL_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const fallback = await response.text();
    throw new Error(fallback || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function fetchCertificates(): Promise<CertificateMetadata[]> {
  return request<CertificateMetadata[]>("/certificates");
}

export function issueCertificate(payload: CertificateIssueRequest): Promise<CertificateIssueResponse> {
  return request<CertificateIssueResponse>("/certificates/issue", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function startManualDnsChallenge(payload: ManualDnsChallengeStartRequest): Promise<ManualDnsChallengeStartResponse> {
  return request<ManualDnsChallengeStartResponse>("/certificates/dns-01/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function completeManualDnsChallenge(payload: ManualDnsChallengeCompleteRequest): Promise<ManualDnsChallengeCompleteResponse> {
  return request<ManualDnsChallengeCompleteResponse>("/certificates/dns-01/complete", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchSystemStatus(): Promise<SystemStatusResponse> {
  return request<SystemStatusResponse>("/system/status");
}

export function fetchLogs(limit = 200): Promise<LogsResponse> {
  return request<LogsResponse>(`/logs?limit=${encodeURIComponent(String(limit))}`);
}

export function fetchNginxStatus(): Promise<NginxConfigSnapshot> {
  return request<NginxConfigSnapshot>("/nginx/status");
}

export function automateNginx(payload: NginxAutomationRequest): Promise<NginxAutomationResponse> {
  return request<NginxAutomationResponse>("/nginx/automate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchRenewalStatus(): Promise<RenewalStatusResponse> {
  return request<RenewalStatusResponse>("/renewal/status");
}

export function runRenewalCycle(): Promise<RenewalRunResponse> {
  return request<RenewalRunResponse>("/renewal/run", {
    method: "POST",
  });
}
