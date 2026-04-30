import { useEffect, useRef } from "react";
import cytoscape, { type Core } from "cytoscape";
import { useForgeStore } from "@/store";

export function AgentTopologyMap() {
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInstance = useRef<Core | null>(null);
  const { tools, resources, status } = useForgeStore();

  useEffect(() => {
    if (!cyRef.current || status !== "connected") return;
    const nodes = [
      { data: { id: "studio", label: "Forge Studio", color: "#60a5fa", type: "studio" } },
      ...tools.map((t) => ({ data: { id: `tool:${t.name}`, label: t.name, color: "#34d399", type: "tool" } })),
      ...resources.map((r) => ({ data: { id: `res:${r.uri}`, label: r.name, color: "#a78bfa", type: "resource" } })),
    ];
    const edges = [
      ...tools.map((t) => ({ data: { id: `s-t:${t.name}`, source: "studio", target: `tool:${t.name}`, type: "tool" } })),
      ...resources.map((r) => ({ data: { id: `s-r:${r.uri}`, source: "studio", target: `res:${r.uri}`, type: "resource" } })),
    ];
    cyInstance.current?.destroy();
    const cy = cytoscape({
      container: cyRef.current,
      elements: { nodes, edges },
      style: [
        { selector: "node", style: { shape: "ellipse", width: 80, height: 36, "background-color": "data(color)", "background-opacity": 0.2, "border-color": "data(color)", "border-width": 2, label: "data(label)", "text-valign": "center", "text-halign": "center", color: "#e2e8f0", "font-size": 10 } },
        { selector: "node[type='studio']", style: { width: 110, height: 44, "font-size": 12, "font-weight": "bold", "background-opacity": 0.35 } },
        { selector: "edge", style: { width: 1.5, "line-color": "#334155", "target-arrow-color": "#475569", "target-arrow-shape": "triangle", "curve-style": "bezier", opacity: 0.7 } },
        { selector: "edge[type='resource']", style: { "line-style": "dashed" } },
      ],
      layout: { name: "cose", animate: false, randomize: false, padding: 24 },
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });
    cy.on("mouseover", "node", (evt) => {
      if (evt.target.id() === "studio") return;
      const targetId = evt.target.id();
      cy.edges().filter((e) => e.data("source") === "studio" && e.data("target") === targetId)
        .style("width", 3).style("opacity", 1);
    });
    cy.on("mouseout", "node", () => { cy.edges().style("width", 1.5).style("opacity", 0.7); });
    cyInstance.current = cy;
    return () => { cy.destroy(); cyInstance.current = null; };
  }, [tools, resources, status]);

  if (status !== "connected" || (tools.length === 0 && resources.length === 0)) {
    return (
      <section style={{ padding: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: "#f1f5f9" }}>Agent Topology</h2>
        <div style={{ height: 160, display: "flex", alignItems: "center", justifyContent: "center", color: "#475569", fontSize: 14, border: "1px dashed #334155", borderRadius: 8 }}>
          Connect to a project to see the MCP tool topology
        </div>
      </section>
    );
  }
  return (
    <section style={{ padding: 24 }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 4, color: "#f1f5f9" }}>Agent Topology</h2>
      <p style={{ fontSize: 12, color: "#64748b", marginBottom: 12 }}>
        <span style={{ color: "#34d399" }}>● tools</span>{" · "}
        <span style={{ color: "#a78bfa" }}>● resources</span>{" — hover for live edge pulse"}
      </p>
      <div ref={cyRef} data-testid="agent-topology" style={{ width: "100%", height: 400, background: "#0f172a", borderRadius: 8, border: "1px solid #1e293b" }} />
    </section>
  );
}
