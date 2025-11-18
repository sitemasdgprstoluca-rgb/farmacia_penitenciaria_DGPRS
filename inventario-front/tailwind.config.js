/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Colores oficiales Subsecretara de Seguridad - Estado de Mxico
        primary: {
          50: '#fef2f3',   // Vino muy claro
          100: '#fde6e8',
          200: '#fbd0d5',
          300: '#f7aab2',
          400: '#f17a8a',
          500: '#e74c64',  // Vino medio
          600: '#d32f4a',  // Vino principal
          700: '#b22342',  // Guinda
          800: '#96203e',
          900: '#7f1d3a',  // Vino oscuro
        },
        accent: {
          50: '#fefce8',   // Dorado muy claro
          100: '#fef9c3',
          200: '#fef08a',
          300: '#fde047',
          400: '#facc15',  // Dorado medio
          500: '#eab308',  // Dorado principal
          600: '#ca8a04',
          700: '#a16207',
          800: '#854d0e',
          900: '#713f12',  // Dorado oscuro
        },
        vino: '#9F2241',    // Color institucional vino
        guinda: '#6B1839',  // Guinda oscuro
        dorado: '#B8860B',  // Dorado institucional
      }
    },
  },
  plugins: [],
}
