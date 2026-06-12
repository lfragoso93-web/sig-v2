/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ── Brand (teal) ───────────────────────────────────────────
        brand: {
          primary: 'var(--color-primary)',
          hover:   'var(--color-primary-hover)',
          active:  'var(--color-primary-active)',
          highlight: 'var(--color-primary-highlight)',
          // escala numérica mantida para compatibilidade com classes existentes
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
        // ── Superfícies — lêem os tokens CSS (mudam com o tema) ────
        bg:       'var(--color-bg)',
        surface: {
          DEFAULT: 'var(--color-surface)',
          2:       'var(--color-surface-2)',
          offset:  'var(--color-surface-offset)',
          offset2: 'var(--color-surface-offset-2)',
          dynamic: 'var(--color-surface-dynamic)',
          // aliases numéricos herdados (apontam para os mesmos tokens)
          950: 'var(--color-bg)',
          900: 'var(--color-bg)',
          800: 'var(--color-surface)',
          700: 'var(--color-surface-2)',
          600: 'var(--color-surface-offset)',
          500: 'var(--color-surface-offset-2)',
        },
        // ── Bordas e divisores ─────────────────────────────────────
        border:  'var(--color-border)',
        divider: 'var(--color-divider)',
        // aliases para classes legadas light-* e dark-* em globals.css
        'light-50':     'var(--color-bg)',
        'light-100':    'var(--color-surface)',
        'light-200':    'var(--color-surface-2)',
        'light-300':    'var(--color-surface-offset)',
        'light-border': 'var(--color-border)',
        'dark-400':     'var(--color-surface-offset)',
        'dark-500':     'var(--color-surface-offset-2)',
        'dark-600':     'var(--color-surface-offset)',
        'dark-700':     'var(--color-surface-2)',
        'dark-800':     'var(--color-surface)',
        'dark-border':  'var(--color-border)',
        'dark-hover':   'var(--color-surface-dynamic)',
        // ── Texto ──────────────────────────────────────────────────
        text: {
          DEFAULT: 'var(--color-text)',
          muted:   'var(--color-text-muted)',
          faint:   'var(--color-text-faint)',
          inverse: 'var(--color-text-inverse)',
        },
        // ── Semânticas ─────────────────────────────────────────────
        positive: 'var(--color-success)',
        negative: 'var(--color-notification)',
        warning:  'var(--color-warning)',
        neutral:  'var(--color-text-muted)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      transitionTimingFunction: {
        smooth: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
}
