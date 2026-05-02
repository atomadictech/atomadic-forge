import * as React from "react";
import { motion } from "motion/react";
import { cn } from "../../utils/cn";

const variants = {
  cyan: "border-cyber-cyan text-cyber-cyan hover:bg-cyber-cyan hover:text-cyber-dark",
  alert: "border-cyber-alert text-cyber-alert hover:bg-cyber-alert hover:text-white",
  success:
    "border-cyber-success text-cyber-success hover:bg-cyber-success hover:text-cyber-dark",
  violet: "border-brand-violet text-brand-violet hover:bg-brand-violet hover:text-white",
} as const;

export function NeonButton({
  children,
  onClick,
  className,
  variant = "cyan",
  disabled = false,
  type = "button",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  variant?: keyof typeof variants;
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
}) {
  return (
    <motion.button
      whileTap={{ scale: disabled ? 1 : 0.97 }}
      onClick={onClick}
      disabled={disabled}
      type={type}
      className={cn(
        "px-6 py-2 border uppercase font-mono tracking-widest text-[11px] transition-colors duration-200 disabled:opacity-40 disabled:cursor-not-allowed",
        variants[variant],
        className,
      )}
    >
      {children}
    </motion.button>
  );
}
