"use client";
import { useEffect, useRef, useState } from "react";
import { useInView } from "motion/react";

export function StatCounter({
  value,
  suffix = "",
  prefix = "",
  label,
  sublabel,
  color = "text-cyber-cyan",
}: {
  value: number;
  suffix?: string;
  prefix?: string;
  label: string;
  sublabel?: string;
  color?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const duration = 1800;
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayed(Math.round(eased * value));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [inView, value]);

  return (
    <div ref={ref} className="flex flex-col items-center gap-1 text-center">
      <div className={`font-mono font-bold tabular-nums ${color}`} style={{ fontSize: "clamp(2rem, 4vw, 3.5rem)" }}>
        {prefix}{displayed.toLocaleString()}{suffix}
      </div>
      <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-cyber-chrome mt-1">{label}</div>
      {sublabel && (
        <div className="font-mono text-[9px] text-monolith-mid max-w-[160px]">{sublabel}</div>
      )}
    </div>
  );
}
