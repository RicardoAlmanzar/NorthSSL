import type { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  eyebrow: string;
  children: ReactNode;
  className?: string;
};

export function SectionCard({ title, eyebrow, children, className = "" }: SectionCardProps) {
  return (
    <section className={`rounded-3xl border border-white/10 bg-slate-900/70 p-5 shadow-glow backdrop-blur-xl ${className}`}>
      <p className="text-xs uppercase tracking-[0.3em] text-cyan-200/70">{eyebrow}</p>
      <h2 className="mt-2 text-xl font-semibold text-white">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}
