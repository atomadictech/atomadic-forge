"use client";
import { motion, useInView } from "motion/react";
import { useRef } from "react";

export function CyberCard({
  children,
  className = "",
  delay = 0,
  accent = "cyan",
  glow = false,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  accent?: "cyan" | "gold" | "alert" | "success" | "violet";
  glow?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  const accentColor = {
    cyan: "border-cyber-cyan/20 hover:border-cyber-cyan/50",
    gold: "border-cyber-gold/20 hover:border-cyber-gold/50",
    alert: "border-cyber-alert/20 hover:border-cyber-alert/50",
    success: "border-cyber-success/20 hover:border-cyber-success/50",
    violet: "border-violet-400/20 hover:border-violet-400/50",
  }[accent];

  const glowColor = {
    cyan: "rgba(34,211,238,0.06)",
    gold: "rgba(245,158,11,0.06)",
    alert: "rgba(244,63,94,0.06)",
    success: "rgba(16,185,129,0.06)",
    violet: "rgba(167,139,250,0.06)",
  }[accent];

  const cornerColor = {
    cyan: "border-cyber-cyan",
    gold: "border-cyber-gold",
    alert: "border-cyber-alert",
    success: "border-cyber-success",
    violet: "border-violet-400",
  }[accent];

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay }}
      className={`relative border ${accentColor} bg-cyber-panel transition-all duration-300 overflow-hidden group ${className}`}
      style={glow ? { boxShadow: `0 0 40px ${glowColor}` } : {}}
    >
      {/* Corner accents */}
      <div className={`absolute top-0 left-0 w-4 h-4 border-t border-l ${cornerColor} opacity-60`} />
      <div className={`absolute top-0 right-0 w-4 h-4 border-t border-r ${cornerColor} opacity-60`} />
      <div className={`absolute bottom-0 left-0 w-4 h-4 border-b border-l ${cornerColor} opacity-60`} />
      <div className={`absolute bottom-0 right-0 w-4 h-4 border-b border-r ${cornerColor} opacity-60`} />
      {/* Scanline */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.015] bg-[linear-gradient(rgba(0,0,0,0)_50%,rgba(0,0,0,0.5)_50%)] bg-[size:100%_3px]" />
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}
