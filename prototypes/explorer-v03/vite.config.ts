import { defineConfig } from "vite";

export default defineConfig(({ isSsrBuild }) => ({
  build: isSsrBuild ? {} : {
    rollupOptions: {
      input: { workspace: "src/workspace.tsx", explore: "src/explore.tsx" },
      output: { entryFileNames: "[name].js" },
    },
  },
}));
