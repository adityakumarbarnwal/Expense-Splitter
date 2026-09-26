/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
        '4xl': '1.5rem',
      },
      boxShadow: {
        'glass':         '0 4px 24px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04)',
        'glass-hover':   '0 8px 32px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06)',
        'glass-elevated':'0 12px 48px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.06)',
        'brand':         '0 4px 16px rgba(99,102,241,0.30)',
        'brand-hover':   '0 8px 24px rgba(99,102,241,0.40)',
        'success':       '0 4px 12px rgba(16,185,129,0.25)',
        'danger':        '0 4px 12px rgba(239,68,68,0.25)',
      },
      backdropBlur: {
        xs:  '4px',
        sm:  '8px',
        md:  '12px',
        lg:  '16px',
        xl:  '20px',
        '2xl': '24px',
      },
      animation: {
        'fade-up':  'fadeUp 0.4s cubic-bezier(0.4,0,0.2,1) both',
        'fade-in':  'fadeIn 0.3s ease both',
        'shimmer':  'shimmer 1.8s infinite',
        'pulse-soft': 'pulseSoft 3s ease-in-out infinite',
        'drift':    'drift 20s ease-in-out infinite alternate',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.7' },
        },
        drift: {
          from: { transform: 'translate(0,0) scale(1)' },
          to:   { transform: 'translate(-30px,40px) scale(1.1)' },
        },
      },
      backgroundImage: {
        'brand-gradient':   'linear-gradient(135deg, #6366f1, #8b5cf6)',
        'success-gradient': 'linear-gradient(135deg, #10b981, #059669)',
        'danger-gradient':  'linear-gradient(135deg, #ef4444, #dc2626)',
        'glass-surface':    'linear-gradient(135deg, rgba(255,255,255,0.80), rgba(255,255,255,0.60))',
      },
    },
  },
  plugins: [],
}
