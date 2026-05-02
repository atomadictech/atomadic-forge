"use client";

import { useEffect } from "react";

export function ServiceWorkerLoader() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .catch((err) => console.warn("[forge-web] sw register failed", err));
  }, []);
  return null;
}
