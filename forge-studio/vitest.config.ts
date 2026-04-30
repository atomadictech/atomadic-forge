import { defineConfig } from "vitest/config";
import path from "path";
export default defineConfig({
  test: { environment: "jsdom", globals: true, include: ["tests/unit/**/*.test.ts"],
    coverage: { provider: "v8", reporter: ["text","json"] } },
  resolve: { alias: {
    "@": path.resolve(__dirname, "./src"),
    "@tauri-apps/api/core": path.resolve(__dirname, "tests/unit/__mocks__/tauri.ts"),
  }},
});