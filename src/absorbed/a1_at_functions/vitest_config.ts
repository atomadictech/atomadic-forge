import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/unit/**/*.test.ts"],
    coverage: { provider: "v8", reporter: ["text", "json"] },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@atomadic/forge-ui-core": path.resolve(
        __dirname,
        "../packages/forge-ui-core/src/index.ts",
      ),
      "@atomadic/forge-ui-core/theme.css": path.resolve(
        __dirname,
        "../packages/forge-ui-core/src/theme/theme.css",
      ),
      "@tauri-apps/api/core": path.resolve(
        __dirname,
        "tests/unit/__mocks__/tauri.ts",
      ),
    },
  },
});
