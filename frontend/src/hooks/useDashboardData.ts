import { useEffect, useState } from "react";

import { fetchCertificates, fetchHealth, fetchLogs, fetchNginxStatus, fetchRenewalStatus, fetchSystemStatus } from "../lib/api";
import type { CertificateMetadata, HealthResponse, LogsResponse, NginxConfigSnapshot, RenewalStatusResponse, SystemStatusResponse } from "../lib/types";

type DashboardState = {
  health: HealthResponse | null;
  certificates: CertificateMetadata[];
  system: SystemStatusResponse | null;
  nginx: NginxConfigSnapshot | null;
  renewal: RenewalStatusResponse | null;
  logs: LogsResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

export function useDashboardData(): DashboardState {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [certificates, setCertificates] = useState<CertificateMetadata[]>([]);
  const [system, setSystem] = useState<SystemStatusResponse | null>(null);
  const [nginx, setNginx] = useState<NginxConfigSnapshot | null>(null);
  const [renewal, setRenewal] = useState<RenewalStatusResponse | null>(null);
  const [logs, setLogs] = useState<LogsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);

    try {
      const [healthData, certificateData, systemData, nginxData, renewalData, logData] = await Promise.all([
        fetchHealth(),
        fetchCertificates(),
        fetchSystemStatus(),
        fetchNginxStatus(),
        fetchRenewalStatus(),
        fetchLogs(),
      ]);

      setHealth(healthData);
      setCertificates(certificateData);
      setSystem(systemData);
      setNginx(nginxData);
      setRenewal(renewalData);
      setLogs(logData);
    } catch (error_) {
      setError(error_ instanceof Error ? error_.message : "Unexpected dashboard error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  return { health, certificates, system, nginx, renewal, logs, loading, error, refresh };
}
