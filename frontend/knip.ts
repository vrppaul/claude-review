import type { KnipConfig } from 'knip';

// What a stylesheet reaches for: Tailwind and its plugins are named in the
// stylesheet, not imported from code
const STYLESHEET_REACH = /@(?:import|plugin)\s+['"]([^'"]+)['"]/g;

/** A stylesheet's @import and @plugin lines, as the imports they are. */
function stylesheetImports(text: string): string {
	return [...text.matchAll(STYLESHEET_REACH)].map((reach) => `import '${reach[1]}';`).join('\n');
}

const config: KnipConfig = {
	// The page reaches knip through index.html, as Vite builds it; `!` marks
	// what --production looks at
	project: ['src/**/*.{ts,svelte,css}!', 'tests/**/*.ts'],
	ignore: ['src/lib/types/generated/**'],
	// The tests are read for what of the page they use, and are themselves
	// held to formatting alone: nothing unused in them is reported
	ignoreIssues: {
		'tests/**': [
			'files',
			'exports',
			'nsExports',
			'types',
			'nsTypes',
			'enumMembers',
			'namespaceMembers',
			'duplicates',
			'cycles'
		]
	},
	// Run by the api:types script, from the Python side of the repository
	ignoreBinaries: ['uv'],
	compilers: { css: stylesheetImports }
};

export default config;
