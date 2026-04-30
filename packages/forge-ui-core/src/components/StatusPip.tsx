import { useForgeStore } from "../store";

export function StatusPip() {
  const { status, projectRoot } = useForgeStore();
  const colors: Record<string, string> = {
    connected: "bg-cyber-success",
    connecting: "bg-yellow-400 animate-pulse",
    error: "bg-cyber-alert",
    disconnected: "bg-cyber-border",
  };
  return (
    <div
      data-testid="status-pip"
      className="flex items-center gap-2 font-mono text-[10px] text-monolith-muted"
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${colors[status] ?? colors.disconnected}`}
      />
      {projectRoot ? (
        <span className="hidden sm:inline truncate max-w-[260px]">
          {projectRoot}
        </span>
      ) : (
        <span>disconnected</span>
      )}
    </div>
  );
}
