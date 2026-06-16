import { formatDistanceToNowStrict } from "date-fns";
import type { Severity } from "./schemas";

export function percent(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  return `${(value * 100).toFixed(digits)}%`;
}

export function number(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  return value.toFixed(digits);
}

export function compactDate(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function relativeTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return `${formatDistanceToNowStrict(new Date(value), { addSuffix: true })}`;
}

export function titleCase(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function severityRank(severity: Severity) {
  return { info: 0, watch: 1, elevated: 2, critical: 3 }[severity];
}
