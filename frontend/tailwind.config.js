/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        haulix: {
          bg: '#0c0d10',
          surface: '#131519',
          card: '#181a20',
          hover: '#1f222a',
          border: 'rgba(255, 255, 255, 0.08)',
          borderActive: 'rgba(255, 255, 255, 0.16)',
          lime: '#d4f933',
          limeHover: '#bef264',
          cyan: '#00f0ff',
          violet: '#8b5cf6',
          amber: '#fbbf24',
          coral: '#ff3366',
        },
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
        },
        darkBg: '#0c0d10',
        darkCard: '#181a20',
        darkBorder: 'rgba(255, 255, 255, 0.08)'
      }
    },
  },
  plugins: [],
}
