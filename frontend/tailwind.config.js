/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        surface: {
          DEFAULT: '#0a0a0f',
          50: '#0f0f18',
          100: '#12121a',
          200: '#181823',
          300: '#1e1e2a',
        },
        glass: {
          DEFAULT: 'rgba(255,255,255,0.03)',
          border: 'rgba(255,255,255,0.06)',
          hover: 'rgba(255,255,255,0.06)',
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
