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
				runes: true
			}
		}),
		svelteTesting() // enables client-side mounting for @testing-library/svelte
	],

	resolve: {
		alias: {
			$lib: resolve(__dirname, 'src/lib')
		}
	},

	build: {
		outDir: resolve(__dirname, '../src/claude_review/static/dist'),
		emptyOutDir: true,
		sourcemap: false, // maps ship in the PyPI wheel and would triple its size
		// elkjs, the 1.4 MB of mermaid's elk layout, never loads: a story's diagram is laid out by dagre, a
		// setting no source may change (lib/dom/diagram.ts). So it is not built, and does not ship
		rolldownOptions: { external: ['elkjs/lib/elk.bundled.js'] }
	},

	test: {
		environment: 'jsdom',
		include: ['tests/**/*.test.ts'],
		setupFiles: ['./tests/setup.ts'],
		// A few workers that stay, each test file in a VM context of its own.
		// The default pool starts a process for every file, and bringing jsdom
		// and the review's modules up in each was 61% of a whole run's work.
		// What vitest's docs warn of in this pool: ES modules in a VM are
		// unstable in Node; a module imported there is never dropped, so a
		// worker's memory grows with every file it runs; and what a native
		// module throws is no `instanceof` the test's own `Error`
		pool: 'vmThreads',
		// Four ran the whole suite as fast as eight or sixteen did, and leave
		// the machine's other cores to whatever else works on it
		maxWorkers: 4,
		// A worker holding more than this is replaced by a fresh one before its
		// next file. Left unset, the limit is the machine's memory shared out
		// between the workers, which a worker never reaches before the machine
		// feels it. Over a whole run of 87 files a worker's heap grew from
		// 73 MB to 684 MB (`vitest run --logHeapUsage`): the limit is half as
		// much again, so no worker is replaced today
		vmMemoryLimit: '1GB',
		// A stub or a spy left behind by a test that failed half way would answer
		// the next test's calls; each test starts from the real globals
		unstubGlobals: true,
		restoreMocks: true,
		// Every run takes the tests in an order of its own, and says which: a
		// test that leans on another's leftovers fails, and its seed repeats it
		sequence: { shuffle: true },
		// Typing into a component is simulated keystroke by keystroke, and the
		// files run in parallel: on a busy machine the default five seconds is
		// not slack, it is a coin toss
		testTimeout: 20_000
	}
});
