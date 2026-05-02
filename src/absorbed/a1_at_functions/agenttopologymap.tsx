import { useEffect, useRef } from "react";
import cytoscape, { type Core } from "cytoscape";
import { useForgeStore } from "../store";
import { ActionableCard } from "./ui/ActionableCard";

export function AgentTopologyMap() {
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInstance = useRef<Core | null>(null);
  const { tools, resources, status } = useForgeStore();

  useEffect(() => {
    if (!cyRef.current || status !== "connected") return;
    const nodes = [
      {
        data: {
          id: "studio",
          label: "Forge UI",
          color: "#60a5fa",
          type: "studio",
        },
      },
      ...tools.map((t) => ({
        data: { id: `tool:${t.name}`, label: t.name, color: "#34d399", type: "tool" },
      })),
      ...resources.map((r) => ({
        data: {
          id: `res:${r.uri}`,
          label: r.name,
          color: "#a78bfa",
          type: "resource",
        },
      })),
    ];
    const edges = [
      ...tools.map((t) => ({
        data: {
          id: `s-t:${t.name}`,
          source: "studio",
          target: `tool:${t.name}`,
          type: "tool",
        },
      })),
      ...resources.map((r) => ({
        data: {
          id: `s-r:${r.uri}`,
          source: "studio",
          target: `res:${r.uri}`,
          type: "resource",
        },
      })),
    ];
    cyInstance.current?.destroy();
    const cy = cytoscape({
      container: cyRef.current,
      elements: { nodes, edges },
      style: [
        {
          selector: "node",
          style: {
            shape: "ellipse",
            width: 80,
            height: 36,
            "background-color": "data(color)",
            "background-opacity": 0.15,
            "border-color": "data(color)",
            "border-width": 1.5,
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            color: "#94a3b8",
            "font-size": 9,
            "font-family": "monospace",
          },
        },
        {
          selector: "node[type='studio']",
          style: {
            width: 110,
            height: 44,
            "font-size": 11,
            "font-weight": "bold",
            "background-opacity": 0.3,
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
        {
          selector: "edge[type='resource']",
          style: { "line-style": "dashed" },
        },
      ],
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      layout: { name: "cose", animate: false, randomize: false, padding: 24 } as any,
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });
    cy.on("mouseover", "node", (evt) => {
      if (evt.target.id() === "studio") return;
      const targetId = evt.target.id();
      cy.edges()
        .filter((e) => e.data("source") === "studio" && e.data("target") === targetId)
        .style("width", 3)
        .style("opacity", 1);
    });
    cy.on("mouseout", "node", () => {
      cy.edges().style("width", 1).style("opacity", 0.7);
    });
    cyInstance.current = cy;
    return () => {
      cy.destroy();
      cyInstance.current = null;
    };
  }, [tools, resources, status]);

  return (
    <div className="p-6 max-w-4xl">
      <ActionableCard title="Agent Topology" delay={0}>
        {status !== "connected" || (tools.length === 0 && resources.length === 0) ? (
          <div className="h-40 flex items-center justify-center border border-dashed border-cyber-border">
            <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-monolith-muted">
              Connect to a project to see the MCP tool topology
            </span>
          </div>
        ) : (
          <>
            <div className="flex gap-4 font-mono text-[9px] uppercase tracking-widest mb-3">
              <span className="text-cyber-success">● {tools.length} tools</span>
              <span className="text-violet-400">● {resources.length} resources</span>
              <span className="text-monolith-muted ml-auto">
                hover for edge pulse
              </span>
            </div>
            <div
              ref={cyRef}
              data-testid="agent-topology"
              className="w-full border border-cyber-border bg-cyber-dark"
              style={{ height: 380 }}
            />
          </>
        )}
      </ActionableCard>
    </div>
  );
}
