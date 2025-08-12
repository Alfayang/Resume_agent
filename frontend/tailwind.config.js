/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        purple: {
          50: '#f0f0ff',
          100: '#e1e1ff',
          200: '#c3c3ff',
          300: '#a5a5ff',
          400: '#8787ff',
          500: '#7879F1',
          600: '#6a6be3',
          700: '#5c5dd5',
          800: '#4e4fc7',
          900: '#4041b9',
        }
      }
    },
  },
  plugins: [],
} 