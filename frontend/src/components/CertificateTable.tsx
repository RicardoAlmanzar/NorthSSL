import type { CertificateMetadata } from "../lib/types";

type CertificateTableProps = {
  certificates: CertificateMetadata[];
};

export function CertificateTable({ certificates }: CertificateTableProps) {
  if (certificates.length === 0) {
    return <p className="text-sm text-slate-400">No certificates have been stored yet.</p>;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10">
      <table className="min-w-full divide-y divide-white/10 text-left text-sm">
        <thead className="bg-white/5 text-slate-300">
          <tr>
            <th className="px-4 py-3 font-medium">Domain</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Provider</th>
            <th className="px-4 py-3 font-medium">Expires</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10 bg-slate-950/30">
          {certificates.map((certificate) => (
            <tr key={certificate.domain}>
              <td className="px-4 py-3 text-white">{certificate.domain}</td>
              <td className="px-4 py-3 text-cyan-200">{certificate.status}</td>
              <td className="px-4 py-3 text-slate-300">{certificate.provider}</td>
              <td className="px-4 py-3 text-slate-300">{certificate.expires_at ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
