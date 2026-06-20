/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0514',
        sidebar: '#140c21',
        primary: '#b066ff',
        secondary: '#1c132b',
        accent: '#9d4edd',
      }
    },
  },
  plugins: [],
}
