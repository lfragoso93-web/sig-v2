/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Paleta escura financeira
        brand: {
          50:  '#edfaf7',
          100: '#d2f4ec',
          200: '#a9e8d9',
          300: '#71d6bf',
          400: '#38bda0',
          500: '#1fa287',
          600: '#15826d',
          700: '#136759',
          800: '#135248',
          900: '#13443d',
          950: '#052923',
        },
        surface: {
          950: '#0a0d14',
          900: '#0f1117',
          800: '#161b27',
          700: '#1e2535',
          600: '#252e42',
          500: '#2e3a50',
        },
        positive: '#22c55e',
        negative: '#ef4444',
        warning:  '#f59e0b',
        neutral:  '#94a3b8',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
