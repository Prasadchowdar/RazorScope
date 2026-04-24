import type { ReactNode } from "react";

type BadgeVariant = "positive" | "negative" | "warning" | "brand" | "brand2" | "neutral";

interface BadgeProps {
  variant?: BadgeVariant;
  size?: "xs" | "sm";
  children: ReactNode;
  className?: string;
}

const VARIANT_STYLES: Record<BadgeVariant, string> = {
  positive: "bg-[rgba(52,211,153,0.12)] text-[#34d399] border border-[rgba(52,211,153,0.2)]",
  negative: "bg-[rgba(248,113,113,0.12)] text-[#f87171] border border-[rgba(248,113,113,0.2)]",
  warning:  "bg-[rgba(251,191,36,0.12)]  text-[#fbbf24] border border-[rgba(251,191,36,0.2)]",
  brand:    "bg-[rgba(127,247,203,0.15)] text-[#7ff7cb] border border-[rgba(127,247,203,0.2)]",
  brand2:   "bg-[rgba(106,179,255,0.15)] text-[#6ab3ff] border border-[rgba(106,179,255,0.2)]",
  neutral:  "bg-[rgba(255,255,255,0.06)] text-[#94a3b8]  border border-[rgba(255,255,255,0.1)]",
};

const SIZE_STYLES: Record<"xs" | "sm", string> = {
  xs: "text-[10px] px-2 py-0.5 rounded-full",
  sm: "text-xs px-2.5 py-1 rounded-lg",
};

export default function Badge({ variant = "neutral", size = "xs", children, className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center font-medium ${VARIANT_STYLES[variant]} ${SIZE_STYLES[size]} ${className}`}>
      {children}
    </span>
  );
}
