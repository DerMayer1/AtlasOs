import type { ReactNode } from "react";

export function Metric({
  label,
  value,
  detail,
  tone = "neutral"
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "neutral" | "good" | "watch" | "critical";
}) {
  return (
    <div className="metric" data-tone={tone}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </div>
  );
}
