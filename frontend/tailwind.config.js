/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "#05070d",
          panel: "#0d1420",
          panel2: "#111a29",
          border: "#1e2836",
          accent: "#2ee6a6",
          accent2: "#8b7cf6",
          danger: "#ff5470",
          warn: "#f5a524",
          muted: "#7c8b9c",
          text: "#e8edf4",
        },
      },
      borderRadius: {
        xl2: "1.25rem",
      },
    },
  },
  plugins: [],
};
