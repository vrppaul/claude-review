import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
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
  ],

  resolve: {
    alias: {
      $lib: resolve(__dirname, 'src/lib'),
    },
  },

  build: {
    outDir: resolve(__dirname, '../src/claude_review/static/dist'),
    emptyOutDir: true,
    sourcemap: true,
  },

  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
    setupFiles: [],
  },
});
