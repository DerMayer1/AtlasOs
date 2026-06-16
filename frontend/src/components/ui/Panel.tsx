import type { ReactNode } from "react";
import { clsx } from "clsx";

export function Panel({
  title,
  subtitle,
  action,
  children,
  className
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx("panel", className)}>
      {(title || subtitle || action) && (
        <header className="panel-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
