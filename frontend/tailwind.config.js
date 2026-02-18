/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        caixa: {
          blue: "#005CA9",
          orange: "#F39200",
        },
      },
    },
  },
  plugins: [],
};
