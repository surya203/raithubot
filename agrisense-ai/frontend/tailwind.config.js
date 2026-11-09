/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        sage: "#949A54",
        earth: "#421B0F",
        bark: "#4E2C11",
        clay: "#744420",
        caramel: "#A56B3A",
        amber: "#AF6D18",
        rust: "#8C490A",
        taupe: "#A78971",
        gold: "#EAA44A",
        cocoa: "#775B44",
        sand: "#E0C9B8",
        cream: "#F7F3EE",
        paper: "#FFFDFB",
      },
      fontFamily: {
        sans: ["Source Sans 3", "Segoe UI", "sans-serif"],
        display: ["Literata", "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(66, 27, 15, 0.06), 0 10px 28px rgba(66, 27, 15, 0.05)",
      },
    },
  },
  plugins: [],
}
