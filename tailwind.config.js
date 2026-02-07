/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          "sans-serif",
        ],
      },
      colors: {
        primary: "#0F766E", // teal-700
        accent: "#F59E0B", // amber-400
        background: "#F8FAFC", // slate-50
        surface: "#ffffff",
      },
    },
  },
  plugins: [],
};
