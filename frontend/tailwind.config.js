/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#05080d",
          secondary: "#0a1018",
          panel: "#0d151f",
        },
        accent: {
          primary: "#56d9ff",
          secondary: "#6f8cff",
        },
        success: "#4ce09a",
        warning: "#f4c95d",
        danger: "#ff647c",
      },
      fontFamily: {
        primary: ["Rajdhani", "Inter", "system-ui", "sans-serif"],
        display: ["Orbitron", "Rajdhani", "sans-serif"],
        mono: ["'Share Tech Mono'", "'JetBrains Mono'", "monospace"],
      },
      borderRadius: {
        sm: "8px",
        md: "14px",
        lg: "22px",
      },
      boxShadow: {
        glow: "0 0 24px rgba(86, 217, 255, 0.35)",
      },
      keyframes: {
        "orb-breathe": {
          "0%, 100%": {
            transform: "scale(0.96)",
            opacity: "0.85",
            filter: "drop-shadow(0 0 12px var(--glow))",
          },
          "50%": {
            transform: "scale(1.04)",
            opacity: "1",
            filter: "drop-shadow(0 0 24px var(--accent-primary))",
          },
        },
        "orb-spin": {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "orb-breathe": "orb-breathe 4s ease-in-out infinite",
        "orb-spin": "orb-spin 12s linear infinite",
        "orb-spin-fast": "orb-spin 3s linear infinite",
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
