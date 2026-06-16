import { clsx } from "clsx";
import type { Severity } from "../../lib/schemas";
import { titleCase } from "../../lib/format";

export function SeverityBadge({ severity }: { severity: Severity | string }) {
  return <span className={clsx("severity-badge", `is-${severity}`)}>{titleCase(severity)}</span>;
}
