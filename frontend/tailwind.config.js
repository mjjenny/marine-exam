/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  corePlugins: {
    // Keep existing theme.css design system intact.
    preflight: false,
  },
  theme: {
    extend: {},
  },
  plugins: [],
};
