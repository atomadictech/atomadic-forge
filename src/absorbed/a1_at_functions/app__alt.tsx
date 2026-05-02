import { invoke } from "@tauri-apps/api/core";
import { useMemo } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ForgeShell, TauriForgeClient } from "@atomadic/forge-ui-core";

const queryClient = new QueryClient();

export function App() {
  const client = useMemo(() => new TauriForgeClient({ invoke }), []);
  return (
    <QueryClientProvider client={queryClient}>
      <ForgeShell client={client} brand="FORGE STUDIO" />
    </QueryClientProvider>
  );
}
