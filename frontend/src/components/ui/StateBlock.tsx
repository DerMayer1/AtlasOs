import type { ReactNode } from "react";

export function StateBlock({
  title,
  detail,
  action
}: {
  title: string;
  detail: string;
  action?: ReactNode;
}) {
  return (
    <div className="state-block">
      <span className="state-rule" />
      <h3>{title}</h3>
      <p>{detail}</p>
      {action}
    </div>
  );
}
