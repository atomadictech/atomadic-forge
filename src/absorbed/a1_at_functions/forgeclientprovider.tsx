import { createContext, useContext, type ReactNode } from "react";
import type { ForgeClient } from "./index";

const ForgeClientContext = createContext<ForgeClient | null>(null);

export interface ForgeClientProviderProps {
  client: ForgeClient;
  children: ReactNode;
}

export function ForgeClientProvider({ client, children }: ForgeClientProviderProps) {
  return (
    <ForgeClientContext.Provider value={client}>{children}</ForgeClientContext.Provider>
  );
}

export function useForgeClient(): ForgeClient {
  const ctx = useContext(ForgeClientContext);
  if (!ctx) {
    throw new Error(
      "useForgeClient: no ForgeClient injected. Wrap your app in <ForgeClientProvider client={...}>",
    );
  }
  return ctx;
}
