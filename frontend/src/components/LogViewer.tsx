type LogViewerProps = {
  lines: string[];
  path: string;
  truncated: boolean;
};

export function LogViewer({ lines, path, truncated }: LogViewerProps) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
      <div className="mb-3 flex items-center justify-between gap-4 text-xs text-slate-400">
        <span>{path}</span>
        <span>{truncated ? "Tail only" : "Complete file"}</span>
      </div>
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950/80 p-4 text-xs leading-6 text-slate-200">
        {lines.length > 0 ? lines.join("\n") : "No log entries available yet."}
      </pre>
    </div>
  );
}
