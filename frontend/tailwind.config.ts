import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Dark surfaces
        dark: {
          900: '#0b0d12',
          800: '#0f1117',
          700: '#14161f',
          600: '#1a1d27',
          500: '#1f2232',
          400: '#252840',
          border: '#2a2d3e',
          hover: '#2f3347',
        },
        // Light surfaces
        light: {
          50:  '#f8f9fc',
          100: '#f1f3f8',
          200: '#e8ebf3',
          300: '#d8dcea',
          border: '#dde0ed',
          hover: '#eceef7',
        },
        // Brand
        brand: {
          primary: '#4f98a3',
          hover:   '#3d8591',
          active:  '#2d6e79',
        },
        // Semantic
        positive: '#22c55e',
        negative: '#f43f5e',
        warning:  '#f59e0b',
        info:     '#3b82f6',
        // Chart
        chart: {
          green:    '#22c55e',
          pink:     '#f43f5e',
          blue:     '#3b82f6',
          blueLight:'#93c5fd',
          orange:   '#f97316',
          purple:   '#a78bfa',
          teal:     '#2dd4bf',
          yellow:   '#fbbf24',
        },
      },
      borderRadius: {
        DEFAULT: '0.5rem',
      },
      transitionTimingFunction: {
        smooth: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
} satisfies Config
