import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "rgba(15, 23, 42, 0.72)",
        panelLine: "rgba(148, 163, 184, 0.16)",
        accent: {
          50: "#ecfeff",
          200: "#a5f3fc",
          400: "#22d3ee",
          500: "#06b6d4",
          700: "#0e7490",
        },
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34, 211, 238, 0.18), 0 24px 80px rgba(2, 6, 23, 0.45)",
      },
    },
  },
  plugins: [],
} satisfies Config;