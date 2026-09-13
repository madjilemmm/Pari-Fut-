/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "#0a0e14",
          panel: "#0f151f",
          border: "#1c2530",
          accent: "#3ddc97",
          danger: "#ff5470",
          muted: "#7c8b9c",
        },
      },
    },
  },
  plugins: [],
};
