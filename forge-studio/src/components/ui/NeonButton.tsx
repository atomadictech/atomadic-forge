import * as React from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

const variants = {
  cyan:    "border-cyber-cyan text-cyber-cyan hover:bg-cyber-cyan hover:text-cyber-dark",
  alert:   "border-cyber-alert text-cyber-alert hover:bg-cyber-alert hover:text-white",
  success: "border-cyber-success text-cyber-success hover:bg-cyber-success hover:text-cyber-dark",
} as const;

export function NeonButton({
  children, onClick, className, variant = "cyan", disabled = false,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  variant?: keyof typeof variants;
  disabled?: boolean;
}) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "px-6 py-2 border uppercase font-mono tracking-widest text-[11px] transition-colors duration-200 disabled:opacity-40 disabled:cursor-not-allowed",
        variants[variant], className,
      )}
    >
      {children}
    </motion.button>
  );
}
