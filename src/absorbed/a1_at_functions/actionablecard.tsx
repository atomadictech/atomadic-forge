import * as React from "react";
import { motion } from "motion/react";
import { cn } from "../../utils/cn";

export function ActionableCard({
  title,
  children,
  className,
  delay = 0,
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className={cn(
        "bg-cyber-panel border border-cyber-border relative overflow-hidden group",
        className,
      )}
    >
      <div className="absolute top-0 right-0 w-6 h-6 border-t border-r border-transparent group-hover:border-cyber-cyan transition-all duration-500 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-6 h-6 border-b border-l border-transparent group-hover:border-cyber-cyan transition-all duration-500 pointer-events-none" />
      <div className="absolute inset-0 pointer-events-none opacity-[0.025] bg-[linear-gradient(rgba(0,0,0,0)_50%,rgba(0,0,0,0.3)_50%)] bg-[size:100%_2px]" />

      {title && (
        <div className="relative px-6 pt-5 pb-4 border-b border-cyber-border flex items-center justify-between">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.3em] text-monolith-muted">
            {title}
          </h3>
          <div className="flex gap-1">
            <div className="w-1 h-1 bg-cyber-cyan/50" />
            <div className="w-1 h-1 bg-cyber-cyan/20" />
          </div>
        </div>
      )}
      <div className="relative z-10 p-6">{children}</div>
    </motion.div>
  );
}
