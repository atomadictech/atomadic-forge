import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Sparkles, Play, ChevronRight, Target } from "lucide-react";
import { useForgeStore } from "../store";
import { useForgeClient } from "../client/context";
import { ActionableCard } from "./ui/ActionableCard";
import { NeonButton } from "./ui/NeonButton";
import type { AgentAction, AgentPlanMode, RiskLevel } from "../types";

const RISK_COLOR: Record<RiskLevel, string> = {
  low: "text-cyber-success border-cyber-success/30",
  medium: "text-amber-400 border-amber-400/30",
  high: "text-cyber-alert border-cyber-alert/30",
};

const VERDICT_COLOR: Record<string, string> = {
  PASS: "text-cyber-success border-cyber-success/40 bg-cyber-success/5",
  FAIL: "text-cyber-alert border-cyber-alert/40 bg-cyber-alert/5",
  NEEDS_WORK: "text-amber-400 border-amber-400/40 bg-amber-400/5",
};

export function AgentPlanDashboard() {
  const {
    projectRoot,
    agentPlan,
    setAgentPlan,
    setError,
  } = useForgeStore();
  const client = useForgeClient();
  const [generating, setGenerating] = useState(false);
  const [stepping, setStepping] = useState<string | null>(null);
  const [goal, setGoal] = useState("");
  const [mode, setMode] = useState<AgentPlanMode>("improve");
  const [topN, setTopN] = useState(5);

  async function handleGenerate() {
    if (!projectRoot) {
      setError("scan a project first");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const plan = await client.plan(projectRoot, {
        goal: goal.trim() || undefined,
        mode,
        top: topN,
        save: true,
      });
      setAgentPlan(plan);
    } catch (e) {
      setError(String(e));
    } finally {
      setGenerating(false);
    }
  }

  async function handleApply(action: AgentAction) {
    if (!agentPlan?.plan_id) {
      setError("generate a plan first");
      return;
    }
    setStepping(action.id);
    setError(null);
    try {
      await client.planStep(agentPlan.plan_id, action.id, true);
      // refresh plan to reflect new state
      if (projectRoot) {
        const refreshed = await client.plan(projectRoot, { goal, mode, top: topN });
        setAgentPlan(refreshed);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setStepping(null);
    }
  }

  return (
    <div className="p-6 space-y-5 max-w-4xl">
      <ActionableCard delay={0}>
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-cyber-cyan">
            <Sparkles size={14} />
            <h2 className="font-mono text-[11px] uppercase tracking-[0.3em]">
              Agent Plan
            </h2>
          </div>
          <p className="font-mono text-[9px] text-monolith-muted">
            Generate ranked action cards for the absorbed/improved repository.
            Each card is a bounded next step the forge can execute.
          </p>

          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Goal (optional) — e.g. ‘ship 0.4 release’"
              className="flex-1 bg-cyber-dark border border-cyber-border text-cyber-chrome font-mono text-xs px-3 py-2 focus:outline-none focus:border-cyber-cyan placeholder:text-monolith-muted"
            />
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as AgentPlanMode)}
              className="bg-cyber-dark border border-cyber-border text-cyber-chrome font-mono text-[10px] uppercase tracking-widest px-3 py-2 focus:outline-none focus:border-cyber-cyan"
            >
              <option value="improve">Improve</option>
              <option value="absorb">Absorb</option>
            </select>
            <input
              type="number"
              min={1}
              max={20}
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value) || 5)}
              className="w-20 bg-cyber-dark border border-cyber-border text-cyber-chrome font-mono text-xs px-3 py-2 focus:outline-none focus:border-cyber-cyan"
              aria-label="top N actions"
            />
            <NeonButton
              onClick={handleGenerate}
              disabled={generating || !projectRoot}
              variant={generating ? "success" : "cyan"}
            >
              {generating ? "Planning…" : "Generate"}
            </NeonButton>
          </div>
        </div>
      </ActionableCard>

      {agentPlan && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`border px-5 py-3 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-[11px] uppercase tracking-widest ${
              VERDICT_COLOR[agentPlan.verdict] ?? VERDICT_COLOR.FAIL
            }`}
          >
            <span className="flex items-center gap-2">
              <Target size={12} />
              Verdict: {agentPlan.verdict}
            </span>
            <span>Mode: {agentPlan.mode}</span>
            <span>{agentPlan.action_count} actions</span>
            <span>{agentPlan.applyable_count} applyable</span>
            {agentPlan.plan_id && (
              <span className="ml-auto text-[9px] text-monolith-muted normal-case tracking-normal">
                id: {agentPlan.plan_id}
              </span>
            )}
          </motion.div>

          <div className="space-y-3">
            <AnimatePresence>
              {agentPlan.top_actions.map((action, i) => (
                <motion.div
                  key={action.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  transition={{ duration: 0.2, delay: i * 0.04 }}
                >
                  <ActionableCard delay={0}>
                    <div className="space-y-3">
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono text-[8px] uppercase tracking-widest text-monolith-muted">
                              {action.kind}
                            </span>
                            <span
                              className={`font-mono text-[8px] uppercase tracking-widest px-1.5 py-0.5 border ${
                                RISK_COLOR[action.risk]
                              }`}
                            >
                              {action.risk} risk
                            </span>
                            <span className="font-mono text-[8px] uppercase tracking-widest text-monolith-muted">
                              scope {action.write_scope}
                            </span>
                          </div>
                          <h3 className="font-mono text-[12px] text-cyber-chrome leading-snug">
                            {action.title}
                          </h3>
                          <p className="font-mono text-[10px] text-monolith-muted mt-1 leading-relaxed">
                            {action.why}
                          </p>
                        </div>
                        {action.applyable && (
                          <NeonButton
                            onClick={() => handleApply(action)}
                            disabled={stepping === action.id}
                            variant={
                              stepping === action.id ? "success" : "cyan"
                            }
                            className="flex-shrink-0"
                          >
                            {stepping === action.id ? (
                              "Applying…"
                            ) : (
                              <span className="flex items-center gap-1.5">
                                <Play size={10} />
                                Apply
                              </span>
                            )}
                          </NeonButton>
                        )}
                      </div>
                      <div className="border-t border-cyber-border pt-2 flex items-center gap-2 font-mono text-[10px] text-monolith-muted">
                        <ChevronRight size={11} />
                        <code className="text-cyber-cyan flex-1 truncate">
                          {action.next_command}
                        </code>
                        {action.related_fcodes && action.related_fcodes.length > 0 && (
                          <span className="text-[8px] uppercase tracking-widest">
                            {action.related_fcodes.join(" · ")}
                          </span>
                        )}
                      </div>
                    </div>
                  </ActionableCard>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {agentPlan.top_actions.length === 0 && (
            <div className="border border-dashed border-cyber-border h-32 flex items-center justify-center">
              <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-cyber-success">
                ⬡ No actions queued — plan is clean
              </span>
            </div>
          )}
        </>
      )}

      {!agentPlan && (
        <div className="border border-dashed border-cyber-border h-32 flex items-center justify-center">
          <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-monolith-muted">
            Generate a plan to surface ranked next actions
          </span>
        </div>
      )}
    </div>
  );
}
