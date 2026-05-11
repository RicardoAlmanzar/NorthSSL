export type HealthResponse = {
  status: string;
  app: string;
  environment: string;
  version: string;
};

export type CertificateMetadata = {
  domain: string;
  provider: string;
  certificate_path: string;
  private_key_path: string;
  issued_at: string;
  expires_at: string | null;
  status: string;
  validation_method: string;
  chain_path: string | null;
  issuer: string | null;
  sans: string[];
  serial_number: string | null;
};

export type CertificateIssueRequest = {
  domain: string;
  provider?: string;
  email?: string | null;
  validation_method?: string;
  webroot_path?: string | null;
};

export type CertificateIssueResponse = {
  message: string;
  certificate: CertificateMetadata;
};

export type ManualDnsChallengeSession = {
  session_id: string;
  domain: string;
  provider: string;
  validation_method: string;
  record_name: string;
  record_value: string;
  started_at: string;
  status: string;
  ready_at: string | null;
  challenge_file_path: string | null;
  ready_file_path: string | null;
  hook_script_path: string | null;
  cleanup_script_path: string | null;
  message: string | null;
};

export type ManualDnsChallengeStartRequest = {
  domain: string;
  provider?: string;
  email?: string | null;
};

export type ManualDnsChallengeStartResponse = {
  message: string;
  session: ManualDnsChallengeSession;
};

export type ManualDnsChallengeCompleteRequest = {
  session_id: string;
  provider?: string;
};

export type ManualDnsChallengeCompleteResponse = {
  message: string;
  certificate: CertificateMetadata;
};

export type DiagnosticsReport = {
  platform: {
    system: string;
    release: string;
    version: string;
    machine: string;
    python_version: string;
    executable: string;
    hostname: string | null;
    fqdn: string | null;
    username: string | null;
    current_directory: string | null;
    distribution: {
      name: string | null;
      distribution_id: string | null;
      version_id: string | null;
      codename: string | null;
      pretty_name: string | null;
    } | null;
  };
  privilege: {
    elevated: boolean;
    mechanism: string;
    username: string | null;
    uid: number | null;
    gid: number | null;
  };
  webservers: Array<{
    name: string;
    installed: boolean;
    active: boolean;
    binary_path: string | null;
    version: string | null;
    service_name: string | null;
    process_id: number | null;
    process_name: string | null;
    config_paths: string[];
    ports: number[];
  }>;
  certbot: {
    installed: boolean;
    binary_path: string | null;
    version: string | null;
    compatible: boolean;
    raw_output: string | null;
  } | null;
  ports: Array<{
    port: number;
    protocol: string;
    occupied: boolean;
    process_id: number | null;
    process_name: string | null;
    command_line: string[];
  }>;
  tools: Array<{
    name: string;
    available: boolean;
    path: string | null;
  }>;
  warnings: string[];
};

export type SystemStatusResponse = {
  settings: Record<string, unknown>;
  diagnostics: DiagnosticsReport;
};

export type LogsResponse = {
  path: string;
  exists: boolean;
  line_count: number;
  truncated: boolean;
  lines: string[];
};

export type NginxServerBlock = {
  file_path: string;
  line_number: number;
  server_names: string[];
  listens: string[];
  ssl_enabled: boolean;
  ssl_certificate: string | null;
  ssl_certificate_key: string | null;
  root: string | null;
  redirect_to_https: boolean;
  proxy_pass: string | null;
  raw: string;
};

export type NginxConfigConflict = {
  kind: string;
  message: string;
  domain: string | null;
  file_paths: string[];
  server_names: string[];
};

export type NginxConfigSnapshot = {
  main_config_path: string;
  site_paths: string[];
  server_blocks: NginxServerBlock[];
  duplicate_domains: string[];
  ssl_domains: string[];
  conflicts: NginxConfigConflict[];
  valid: boolean;
  parsed_at: string | null;
};

export type NginxAutomationRequest = {
  domain: string;
  email?: string | null;
  validation_method?: string;
  provider?: string;
  document_root?: string;
  upstream_host?: string;
  upstream_port?: number;
  redirect_http?: boolean;
};

export type NginxDeploymentResult = {
  success: boolean;
  domain: string;
  config_path: string;
  backup_path: string | null;
  validated: boolean;
  reloaded: boolean;
  rolled_back: boolean;
  message: string;
  stdout: string | null;
  stderr: string | null;
  conflicts: NginxConfigConflict[];
};

export type NginxAutomationResponse = {
  success: boolean;
  message: string;
  certificate: CertificateMetadata | null;
  deployment: NginxDeploymentResult | null;
  config: NginxConfigSnapshot | null;
};

export type CertificateHealthSnapshot = {
  domain: string;
  certificate_path: string | null;
  expires_at: string | null;
  days_remaining: number | null;
  issuer: string | null;
  sans: string[];
  valid: boolean;
  renewal_due: boolean;
  https_reachable: boolean | null;
  tls_version: string | null;
  tls_error: string | null;
  checked_at: string | null;
};

export type RenewalJobSnapshot = {
  name: string;
  enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  last_message: string | null;
};

export type RenewalRunResult = {
  domain: string;
  success: boolean;
  message: string;
  attempted_at: string;
  previous_expires_at: string | null;
  new_expires_at: string | null;
  retries_used: number;
  locked: boolean;
};

export type RenewalStatusResponse = {
  enabled: boolean;
  policy: Record<string, unknown>;
  jobs: RenewalJobSnapshot[];
  health: CertificateHealthSnapshot[];
};

export type RenewalRunResponse = {
  success: boolean;
  message: string;
  results: RenewalRunResult[];
};
