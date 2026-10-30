import { ReactNode } from "react";

export interface EmptyStateProps {
  /** What isn't here yet, in the words the wireframe uses. */
  children: ReactNode;
  /** The next step, such as a Button, where the design has one. */
  action?: ReactNode;
}

/** Stands in for a list or section with nothing in it yet (C8, C6). */
export default function EmptyState({ children, action }: EmptyStateProps) {
  return (
    <div className="margin-bottom-4">
      <p className="margin-top-1">{children}</p>
      {action}
    </div>
  );
}
