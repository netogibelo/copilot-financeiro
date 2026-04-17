/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
        display: ["var(--font-cabinet)", "var(--font-geist-sans)", "sans-serif"],
      },
      colors: {
        brand: {
          50:  "#f0fdf4",
          100: "#dcfce7",
          200: "#bbf7d0",
          300: "#86efac",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          800: "#166534",
          900: "#14532d",
          950: "#052e16",
        },
        surface: {
          0: "#ffffff",
          50: "#f9fafb",
          100: "#f3f4f6",
          200: "#e5e7eb",
          800: "#1a1d23",
          900: "#111418",
          950: "#0a0d11",
        },
        accent: {
          emerald: "#10b981",
          violet: "#8b5cf6",
          amber: "#f59e0b",
          rose: "#f43f5e",
          sky: "#0ea5e9",
        },
      },
      borderRadius: {
        "4xl": "2rem",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "mesh-green": "radial-gradient(at 40% 20%, hsla(150,80%,25%,1) 0px, transparent 50%), radial-gradient(at 80% 0%, hsla(143,70%,20%,1) 0px, transparent 50%), radial-gradient(at 0% 50%, hsla(160,90%,15%,1) 0px, transparent 50%)",
      },
      animation: {
        "slide-in": "slideIn 0.3s ease-out",
        "fade-up": "fadeUp 0.4s ease-out",
        "pulse-soft": "pulseSoft 2s infinite",
        "shimmer": "shimmer 1.5s infinite",
      },
      keyframes: {
        slideIn: {
          "0%": { transform: "translateX(-100%)", opacity: 0 },
          "100%": { transform: "translateX(0)", opacity: 1 },
        },
        fadeUp: {
          "0%": { transform: "translateY(16px)", opacity: 0 },
          "100%": { transform: "translateY(0)", opacity: 1 },
        },
        pulseSoft: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.7 },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};
