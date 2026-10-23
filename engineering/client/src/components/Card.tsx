import { ReactNode } from "react";

export interface CardProps {
  children: ReactNode;
  className?: string;
}

/** A white, rounded, shadowed panel around its children. */
function Card({ children, className }: CardProps) {
  return (
    <div
      className={["bg-white padding-4 shadow-2 radius-lg", className].join(" ")}
    >
      {children}
    </div>
  );
}

export default Card;
