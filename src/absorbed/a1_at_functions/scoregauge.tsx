import { motion } from "motion/react";
import { cn } from "../../utils/cn";

export function ScoreGauge({ score, label }: { score: number; label?: string }) {
  const radius = 60;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;
  const ok = score >= 75;

  return (
    <div className="relative flex items-center justify-center w-40 h-40">
      <svg className="w-full h-full -rotate-90">
        <circle
          cx="80"
          cy="80"
          r={radius}
          stroke="#1a1a1a"
          strokeWidth="10"
          fill="transparent"
        />
        <motion.circle
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.4, ease: "easeOut" }}
          cx="80"
          cy="80"
          r={radius}
          stroke={ok ? "#10b981" : "#f43f5e"}
          strokeWidth="10"
          fill="transparent"
          strokeDasharray={circ}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span
          className={cn(
            "text-3xl font-mono font-bold",
            ok ? "text-cyber-success" : "text-cyber-alert",
          )}
        >
          {score}
        </span>
        <span className="text-[9px] font-mono text-monolith-muted uppercase tracking-widest mt-1">
          {label ?? (ok ? "Ready" : "Violations")}
        </span>
      </div>
    </div>
  );
}
