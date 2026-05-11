import { FormEvent, useMemo, useState } from "react";

import { automateNginx, completeManualDnsChallenge, issueCertificate, startManualDnsChallenge } from "./lib/api";
import { runRenewalCycle } from "./lib/api";
import { CertificateTable } from "./components/CertificateTable";
import { LogViewer } from "./components/LogViewer";
import { MetricCard } from "./components/MetricCard";
import { SectionCard } from "./components/SectionCard";
import { Shell } from "./components/Shell";
import { useDashboardData } from "./hooks/useDashboardData";
import type { ManualDnsChallengeSession } from "./lib/types";

export default function App() {
  const { health, certificates, system, nginx, renewal, logs, loading, error, refresh } = useDashboardData();
  const [domain, setDomain] = useState("example.com");
  const [email, setEmail] = useState("");
  const [provider, setProvider] = useState("self-signed");
  const [validationMethod, setValidationMethod] = useState("self-signed");
  const [documentRoot, setDocumentRoot] = useState("/var/www/html");
  const [upstreamHost, setUpstreamHost] = useState("127.0.0.1");
  const [upstreamPort, setUpstreamPort] = useState("80");
  const [autoConfigureNginx, setAutoConfigureNginx] = useState(true);
  const [dnsSession, setDnsSession] = useState<ManualDnsChallengeSession | null>(null);
  const [formState, setFormState] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [formMessage, setFormMessage] = useState("");
  const [renewalState, setRenewalState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [renewalMessage, setRenewalMessage] = useState("");

  const diagnostics = system?.diagnostics;

  const summaryItems = useMemo(
    () => [
      {
        label: "Certificates",
        value: String(certificates.length),
        hint: certificates.length === 1 ? "Stored certificate" : "Stored certificates",
      },
      {
        label: "Certbot",
        value: diagnostics?.certbot?.installed ? "Ready" : "Missing",
        hint: diagnostics?.certbot?.compatible ? "Compatible with this host" : "Needs installation or path fix",
      },
      {
        label: "Privilege",
        value: diagnostics?.privilege.elevated ? "Elevated" : "Standard",
        hint: diagnostics?.privilege.mechanism ?? "Privilege snapshot unavailable",
      },
      {
        label: "Nginx",
        value: nginx?.valid ? String(nginx.server_blocks.length) : "Unavailable",
        hint: nginx?.main_config_path ?? "Nginx config discovery unavailable",
      },
      {
        label: "Logs",
        value: logs?.exists ? String(logs.line_count) : "Missing",
        hint: logs?.path ?? "Log file path unavailable",
      },
    ],
    [certificates.length, diagnostics, logs, nginx],
  );

  async function handleRunRenewalCycle() {
    setRenewalState("running");
    setRenewalMessage("");

    try {
      const response = await runRenewalCycle();
      setRenewalState(response.success ? "done" : "error");
      setRenewalMessage(response.message);
      await refresh();
    } catch (error_) {
      setRenewalState("error");
      setRenewalMessage(error_ instanceof Error ? error_.message : "Renewal cycle failed");
    }
  }

  const renewalDueCount = renewal?.health.filter((item) => item.renewal_due).length ?? 0;

  const isManualDns = validationMethod === "dns-manual";

  async function handleIssueSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormState("submitting");
    setFormMessage("");
    setDnsSession(null);

    try {
      if (isManualDns) {
        const response = await startManualDnsChallenge({
          domain,
          provider,
          email: email || null,
        });

        setDnsSession(response.session);
        setFormState("success");
        setFormMessage(response.message);
        await refresh();
        return;
      }

      if (autoConfigureNginx) {
        const response = await automateNginx({
          domain,
          provider,
          email: email || null,
          validation_method: validationMethod,
          document_root: documentRoot,
          upstream_host: upstreamHost,
          upstream_port: Number(upstreamPort),
          redirect_http: true,
        });

        setFormState(response.success ? "success" : "error");
        setFormMessage(response.message);
      } else {
        const response = await issueCertificate({
          domain,
          provider,
          email: email || null,
          validation_method: validationMethod,
          webroot_path: documentRoot,
        });

        setFormState("success");
        setFormMessage(response.message);
      }

      await refresh();
    } catch (error_) {
      setFormState("error");
      setFormMessage(error_ instanceof Error ? error_.message : "Certificate issuance failed");
    }
  }

  async function handleCompleteManualDnsChallenge() {
    if (!dnsSession) {
      return;
    }

    setFormState("submitting");
    setFormMessage("");

    try {
      const response = await completeManualDnsChallenge({
        session_id: dnsSession.session_id,
        provider,
      });

      setFormState("success");
      setFormMessage(response.message);
      setDnsSession(null);
      await refresh();
    } catch (error_) {
      setFormState("error");
      setFormMessage(error_ instanceof Error ? error_.message : "DNS-01 completion failed");
    }
  }

  return (
    <Shell
      title="Control plane for certificates and server discovery"
      subtitle="NorthSSL pairs a FastAPI backend with a React/Tauri dashboard so operators can inspect the host, review stored certificates, and trigger issuance from one place."
    >
      <div className="grid gap-4 xl:grid-cols-5">
        {summaryItems.map((item) => (
          <MetricCard key={item.label} label={item.label} value={item.value} hint={item.hint} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.9fr]">
        <SectionCard eyebrow="Operations" title="Issue a certificate and automate nginx">
          <form className="grid gap-4" onSubmit={handleIssueSubmit}>
            <label className="grid gap-2 text-sm text-slate-300">
              Domain
              <input
                className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
                placeholder="app.example.com"
              />
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="grid gap-2 text-sm text-slate-300">
                Provider
                <select
                  className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                  value={provider}
                  onChange={(event) => {
                    const nextProvider = event.target.value;
                    setProvider(nextProvider);
                    if (nextProvider === "self-signed") {
                      setValidationMethod("self-signed");
                    } else if (validationMethod === "self-signed") {
                      setValidationMethod("standalone");
                    }
                  }}
                >
                  <option value="self-signed">self-signed</option>
                  <option value="certbot">certbot</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm text-slate-300">
                Email
                <input
                  className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="admin@example.com"
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-300">
                Validation
                <select
                  className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                  value={validationMethod}
                  onChange={(event) => setValidationMethod(event.target.value)}
                >
                  <option value="self-signed">self-signed</option>
                  <option value="standalone">standalone</option>
                  <option value="webroot">webroot</option>
                  <option value="dns-01">dns-01</option>
                  <option value="dns-manual">dns-manual</option>
                </select>
              </label>
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">
              <input
                type="checkbox"
                checked={autoConfigureNginx}
                onChange={(event) => setAutoConfigureNginx(event.target.checked)}
                disabled={isManualDns}
                className="h-4 w-4 rounded border-white/20 bg-slate-900"
              />
              Auto-configure nginx after issuance {isManualDns ? "(disabled for dns-manual)" : ""}
            </label>

            <div className="grid gap-4 md:grid-cols-3">
              <label className="grid gap-2 text-sm text-slate-300">
                Document root
                <input
                  className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                  value={documentRoot}
                  onChange={(event) => setDocumentRoot(event.target.value)}
                  placeholder="/var/www/html"
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-300">
                Upstream host
                <input
                  className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                  value={upstreamHost}
                  onChange={(event) => setUpstreamHost(event.target.value)}
                  placeholder="127.0.0.1"
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-300">
                Upstream port
                <input
                  className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                  value={upstreamPort}
                  onChange={(event) => setUpstreamPort(event.target.value)}
                  placeholder="80"
                />
              </label>
            </div>

            <button
              className="inline-flex items-center justify-center rounded-2xl bg-cyan-400 px-4 py-3 font-medium text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-70"
              disabled={formState === "submitting"}
            >
              {formState === "submitting"
                ? "Applying..."
                : isManualDns
                  ? "Start DNS-01 challenge"
                  : autoConfigureNginx
                    ? "Issue and configure nginx"
                    : "Issue certificate"}
            </button>

            {dnsSession ? (
              <div className="grid gap-3 rounded-2xl border border-cyan-400/30 bg-cyan-500/10 px-4 py-4 text-sm text-cyan-50">
                <p className="font-medium">Manual DNS-01 challenge ready</p>
                <p>Record name: <span className="font-mono">{dnsSession.record_name}</span></p>
                <p>Record value: <span className="font-mono break-all">{dnsSession.record_value}</span></p>
                <p>Add that TXT record in Hostinger, wait for DNS propagation, then continue.</p>
                <button
                  type="button"
                  className="inline-flex items-center justify-center rounded-2xl bg-cyan-300 px-4 py-3 font-medium text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-70"
                  onClick={handleCompleteManualDnsChallenge}
                  disabled={formState === "submitting"}
                >
                  I added the TXT record, continue
                </button>
              </div>
            ) : null}

            {formMessage ? (
              <p
                className={`rounded-2xl border px-4 py-3 text-sm ${
                  formState === "error"
                    ? "border-rose-400/30 bg-rose-500/10 text-rose-100"
                    : "border-emerald-400/30 bg-emerald-500/10 text-emerald-100"
                }`}
              >
                {formMessage}
              </p>
            ) : null}
          </form>
        </SectionCard>

        <SectionCard eyebrow="Live state" title="Health and control surface">
          <div className="grid gap-4 text-sm text-slate-300">
            <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <span>API</span>
              <span className="text-cyan-200">{health?.status ?? "loading"}</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <span>Nginx config</span>
              <span className="text-slate-100">{nginx?.main_config_path ?? "unknown"}</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <span>Server blocks</span>
              <span className="text-slate-100">{nginx?.server_blocks.length ?? 0}</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <span>Duplicate domains</span>
              <span className="text-slate-100">{nginx?.duplicate_domains.length ?? 0}</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <span>API base URL</span>
              <span className="text-slate-100">{import.meta.env.VITE_NORTHSSL_API_URL ?? "http://127.0.0.1:8000"}</span>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <SectionCard eyebrow="Inventory" title="Stored certificates">
          {loading && certificates.length === 0 ? (
            <p className="text-sm text-slate-400">Loading certificate inventory...</p>
          ) : (
            <CertificateTable certificates={certificates} />
          )}
          {error ? <p className="mt-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</p> : null}
        </SectionCard>

        <SectionCard eyebrow="System" title="Host discovery">
          {diagnostics ? (
            <div className="grid gap-4 text-sm text-slate-300">
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Platform</p>
                <p className="mt-2 text-slate-100">
                  {diagnostics.platform.system} {diagnostics.platform.release}
                </p>
                <p className="mt-1 text-slate-400">
                  {diagnostics.platform.machine} · {diagnostics.platform.python_version}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Privilege</p>
                <p className="mt-2 text-slate-100">{diagnostics.privilege.elevated ? "Elevated" : "Standard"}</p>
                <p className="mt-1 text-slate-400">{diagnostics.privilege.mechanism}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Warnings</p>
                <ul className="mt-2 space-y-2">
                  {diagnostics.warnings.length > 0 ? diagnostics.warnings.map((warning) => <li key={warning}>• {warning}</li>) : <li>No warnings reported.</li>}
                </ul>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Loading system status...</p>
          )}
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <SectionCard eyebrow="Renewal" title="Automatic renewal and monitoring">
          <div className="grid gap-4 text-sm text-slate-300">
            <div className="grid gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <div className="flex items-center justify-between">
                <span>Scheduler</span>
                <span className={renewal?.enabled ? "text-emerald-200" : "text-rose-200"}>{renewal?.enabled ? "Enabled" : "Disabled"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Due certificates</span>
                <span className="text-slate-100">{renewalDueCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Scan interval</span>
                <span className="text-slate-100">{typeof renewal?.policy.check_interval_seconds === "number" ? `${renewal.policy.check_interval_seconds}s` : "unknown"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Renew before</span>
                <span className="text-slate-100">{typeof renewal?.policy.renew_before_days === "number" ? `${renewal.policy.renew_before_days} days` : "unknown"}</span>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Jobs</p>
              <ul className="mt-2 space-y-2">
                {renewal?.jobs.length ? renewal.jobs.map((job) => <li key={job.name}>• {job.name} {job.enabled ? "(scheduled)" : "(stopped)"}</li>) : <li>No scheduler jobs loaded.</li>}
              </ul>
            </div>

            <button
              className="inline-flex items-center justify-center rounded-2xl bg-emerald-400 px-4 py-3 font-medium text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-70"
              onClick={handleRunRenewalCycle}
              disabled={renewalState === "running"}
            >
              {renewalState === "running" ? "Running renewal cycle..." : "Run renewal cycle now"}
            </button>

            {renewalMessage ? (
              <p
                className={`rounded-2xl border px-4 py-3 text-sm ${
                  renewalState === "error"
                    ? "border-rose-400/30 bg-rose-500/10 text-rose-100"
                    : "border-emerald-400/30 bg-emerald-500/10 text-emerald-100"
                }`}
              >
                {renewalMessage}
              </p>
            ) : null}
          </div>
        </SectionCard>

        <SectionCard eyebrow="SSL health" title="Certificates near expiry">
          {renewal ? (
            <div className="grid gap-3 text-sm text-slate-300">
              {renewal.health.slice(0, 6).map((item) => (
                <div key={item.domain} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-100">{item.domain}</span>
                    <span className={item.renewal_due ? "text-amber-200" : item.https_reachable === false ? "text-rose-200" : "text-emerald-200"}>
                      {item.renewal_due ? "Renew soon" : item.https_reachable === false ? "TLS error" : "Healthy"}
                    </span>
                  </div>
                  <p className="mt-2 text-slate-400">{item.days_remaining === null ? "Unknown expiration" : `${item.days_remaining} days remaining`}</p>
                </div>
              ))}
              {renewal.health.length === 0 ? <p className="text-sm text-slate-400">No certificates tracked by the renewal engine yet.</p> : null}
            </div>
          ) : (
            <p className="text-sm text-slate-400">Loading renewal health...</p>
          )}
        </SectionCard>

        <SectionCard eyebrow="Nginx" title="Applied configs and conflicts">
          {nginx ? (
            <div className="grid gap-4 text-sm text-slate-300">
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Site paths</p>
                <ul className="mt-2 space-y-1">
                  {nginx.site_paths.length > 0 ? nginx.site_paths.map((path) => <li key={path}>{path}</li>) : <li>No site paths discovered.</li>}
                </ul>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">SSL-enabled domains</p>
                <p className="mt-2 text-slate-100">{nginx.ssl_domains.length > 0 ? nginx.ssl_domains.join(", ") : "None yet"}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Duplicate domains</p>
                <p className="mt-2 text-slate-100">{nginx.duplicate_domains.length > 0 ? nginx.duplicate_domains.join(", ") : "None"}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Conflicts</p>
                <ul className="mt-2 space-y-2">
                  {nginx.conflicts.length > 0 ? nginx.conflicts.map((conflict) => <li key={`${conflict.kind}-${conflict.message}`}>• {conflict.message}</li>) : <li>No conflicts detected.</li>}
                </ul>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Loading Nginx status...</p>
          )}
        </SectionCard>

        <SectionCard eyebrow="Logs" title="Recent API output">
          {logs ? <LogViewer lines={logs.lines} path={logs.path} truncated={logs.truncated} /> : <p className="text-sm text-slate-400">Loading logs...</p>}
        </SectionCard>
      </div>
    </Shell>
  );
}
