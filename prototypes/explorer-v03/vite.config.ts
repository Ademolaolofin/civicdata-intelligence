import { defineConfig } from "vite";

export default defineConfig(({ isSsrBuild }) => ({
  build: isSsrBuild ? {} : {
    rollupOptions: {
      input: "src/workspace.tsx",
      output: { entryFileNames: "workspace.js" },
    },
  },
}));
