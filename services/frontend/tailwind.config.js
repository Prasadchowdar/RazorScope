/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          0: '#080f1a',
          1: '#0d1726',
          2: '#111e2e',
        },
        brand: {
          DEFAULT: '#7ff7cb',
          dim: 'rgba(127,247,203,0.15)',
          2: '#6ab3ff',
        },
        positive: {
          DEFAULT: '#34d399',
          dim: 'rgba(52,211,153,0.12)',
        },
        negative: {
          DEFAULT: '#f87171',
          dim: 'rgba(248,113,113,0.12)',
        },
        warning: {
          DEFAULT: '#fbbf24',
          dim: 'rgba(251,191,36,0.12)',
        },
      },
      fontFamily: {
        sans: ['"Geist"', '"Instrument Sans"', 'sans-serif'],
        mono: ['"Geist Mono"', '"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}
