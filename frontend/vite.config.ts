import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { svelteTesting } from '@testing-library/svelte/vite';
import tailwindcss from '@tailwindcss/vite';
import { resolve } from 'path';

export default defineConfig({
  plugins: [
    tailwindcss(),
    svelte({
      compilerOptions: {
        runes: true,
      },
    }),
    svelteTesting(), // enables client-side mounting for @testing-library/svelte
  ],

  resolve: {
    alias: {
      $lib: resolve(__dirname, 'src/lib'),
    },
  },

  build: {
    outDir: resolve(__dirname, '../src/claude_review/static/dist'),
    emptyOutDir: true,
    sourcemap: false, // maps ship in the PyPI wheel and would triple its size
  },

  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
    setupFiles: ['./tests/setup.ts'],
  },
});
