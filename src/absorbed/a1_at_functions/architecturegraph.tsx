import { useEffect, useRef } from "react";
import cytoscape, { type Core } from "cytoscape";
import { useForgeStore } from "../store";
import { ActionableCard } from "./ui/ActionableCard";
import type { Tier } from "../types";

const TC: Record<Tier, string> = {
  a0: "#818cf8",
  a1: "#34d399",
  a2: "#60a5fa",
  a3: "#f472b6",
  a4: "#fb923c",
};
const TL: Record<Tier, string> = {
  a0: "a0\nConstants",
  a1: "a1\nFunctions",
  a2: "a2\nComposites",
  a3: "a3\nFeatures",
  a4: "a4\nOrchestration",
};
const EDGES: [Tier, Tier][] = [
  ["a1", "a0"],
  ["a2", "a0"],
  ["a2", "a1"],
  ["a3", "a0"],
  ["a3", "a1"],
  ["a3", "a2"],
  ["a4", "a0"],
  ["a4", "a1"],
  ["a4", "a2"],
  ["a4", "a3"],
];

export function ArchitectureGraph() {
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInstance = useRef<Core | null>(null);
  const { scoutReport, selectedTier, setSelectedTier } = useForgeStore();

  useEffect(() => {
    if (!cyRef.current) return;
    const tiers: Tier[] = ["a0", "a1", "a2", "a3", "a4"];
    const counts = scoutReport
      ? Object.fromEntries(
          tiers.map((t) => [
            t,
            scoutReport.symbols.filter((s) => s.tier === t).length,
          ]),
        )
      : Object.fromEntries(tiers.map((t) => [t, 0]));
    const nodes = tiers.map((tier, i) => ({
      data: {
        id: tier,
        label: TL[tier],
        count: counts[tier] ?? 0,
        color: TC[tier],
      },
      position: { x: 80 + i * 110, y: 420 - i * 90 },
    }));
    const edges = EDGES.map(([from, to]) => ({
      data: { id: `${from}-${to}`, source: from, target: to },
    }));
    cyInstance.current?.destroy();
    const cy = cytoscape({
      container: cyRef.current,
      elements: { nodes, edges },
      style: [
        {
          selector: "node",
          style: {
            shape: "round-rectangle",
            width: 120,
            height: 56,
            "background-color": "data(color)",
            "background-opacity": 0.12,
            "border-color": "data(color)",
            "border-width": 1.5,
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            color: "#94a3b8",
            "font-size": 10,
            "font-family": "monospace",
            "white-space": "pre",
            "text-wrap": "wrap",
          } as Record<string, unknown>,
        },
        {
          selector: "node:selected",
          style: {
            "background-opacity": 0.35,
            "border-width": 2.5,
            color: "#e2e8f0",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": "#1a1a1a",
            "target-arrow-color": "#334155",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.7,
          },
        },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ] as any,
      layout: { name: "preset" },
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });
    cy.on("tap", "node", (evt) => {
      const tier = evt.target.id() as Tier;
      setSelectedTier(selectedTier === tier ? null : tier);
    });
    cyInstance.current = cy;
    return () => {
      cy.destroy();
      cyInstance.current = null;
    };
  }, [scoutReport]);

  useEffect(() => {
    const cy = cyInstance.current;
    if (!cy) return;
    cy.nodes().forEach((node) => {
      const sel = node.id() === selectedTier;
      node.style("background-opacity", sel ? 0.4 : 0.12);
      node.style("border-width", sel ? 2.5 : 1.5);
      node.style("color", sel ? "#e2e8f0" : "#94a3b8");
    });
  }, [selectedTier]);

  return (
    <div className="p-6 max-w-4xl">
      <ActionableCard title="Architecture Graph" delay={0}>
        <p className="font-mono text-[9px] uppercase tracking-widest text-monolith-muted mb-4">
          5-tier monadic law — edges show allowed upward-only imports · click a
          node to filter symbols
        </p>
        {scoutReport ? (
          <div
            ref={cyRef}
            data-testid="arch-graph"
            className="w-full rounded-none border border-cyber-border bg-cyber-dark"
            style={{ height: 520 }}
          />
        ) : (
          <div className="h-40 flex items-center justify-center border border-dashed border-cyber-border">
            <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-monolith-muted">
              Scan a project to render the architecture graph
            </span>
          </div>
        )}
      </ActionableCard>
    </div>
  );
}
