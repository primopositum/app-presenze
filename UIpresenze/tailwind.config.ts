import type { Config } from 'tailwindcss';
import defaultTheme from 'tailwindcss/defaultTheme';
import forms from '@tailwindcss/forms';
import typography from '@tailwindcss/typography';
import plugin from 'tailwindcss/plugin';

const config: Config = {
  darkMode: 'class', 
  content: [
    './src/**/*.{html,js,svelte,ts}', // scansiona tutti i file Svelte/TS/JS/HTML
  ],
  plugins: [
    forms,
    typography,
    plugin(({ addVariant }) => {
      addVariant('dark-hover', ['.dark &:hover']);
      addVariant('dark-active', ['.dark &:active']);
    }),
  ],
};

export default config;
