/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F7F3EC",
        card: "#FFFDF9",
        ink: { DEFAULT: "#2B2A27", soft: "#5E5A52", faint: "#8F897E" },
        line: "#E6DFD3",
        sage: { 50: "#EEF3EE", 100: "#DCE7DC", 300: "#9DB89F", 500: "#5F8A66", 600: "#4C7353", 700: "#3B5A41" },
        clay: { 50: "#FBEFE9", 100: "#F5DCCF", 400: "#D98B66", 500: "#C9714A", 600: "#A9583A" },
        honey: { 50: "#FBF4E2", 100: "#F5E5B8", 500: "#D9A63A", 600: "#B88A26" },
        dusk: { 50: "#EEF0F7", 100: "#DADFEE", 500: "#6672A8", 600: "#525D90" },
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(43,42,39,.04), 0 4px 16px rgba(43,42,39,.06)",
        lift: "0 2px 4px rgba(43,42,39,.05), 0 12px 32px rgba(43,42,39,.10)",
      },
      keyframes: {
        pop: { "0%": { transform: "scale(.92)", opacity: "0" }, "60%": { transform: "scale(1.03)", opacity: "1" }, "100%": { transform: "scale(1)" } },
        rise: { "0%": { transform: "translateY(8px)", opacity: "0" }, "100%": { transform: "translateY(0)", opacity: "1" } },
        glow: { "0%,100%": { boxShadow: "0 0 0 0 rgba(217,166,58,0)" }, "50%": { boxShadow: "0 0 0 6px rgba(217,166,58,.25)" } },
        toast: { "0%": { transform: "translateY(-12px)", opacity: "0" }, "10%,85%": { transform: "translateY(0)", opacity: "1" }, "100%": { transform: "translateY(-12px)", opacity: "0" } },
      },
      animation: {
        pop: "pop .45s ease-out both",
        rise: "rise .35s ease-out both",
        glow: "glow 1.6s ease-in-out 2",
        toast: "toast 3.2s ease-in-out both",
      },
    },
  },
  plugins: [],
};
