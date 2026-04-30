"use client";

import { useMemo } from "react";
import { ForgeShell, HttpForgeClient } from "@atomadic/forge-ui-core";
import { InstallPwaButton } from "./InstallPwaButton";
import { ServiceWorkerLoader } from "./ServiceWorkerLoader";

export function ForgeApp() {
  const client = useMemo(() => new HttpForgeClient({ baseUrl: "/api/forge" }), []);
  return (
    <>
      <ServiceWorkerLoader />
      <ForgeShell
        client={client}
        brand="FORGE WEB"
        topBarRight={<InstallPwaButton />}
      />
    </>
  );
}
