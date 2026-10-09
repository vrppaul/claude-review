import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import svelte from 'eslint-plugin-svelte';
import svelteConfig from './svelte.config.js';

// What each part of src/lib may build on. A part importing one it is not
// listed with fails here: nothing reaches up into what is built on it, and
// components, which build on everything, are built on by nothing but
// components.
const LAYERS = {
	types: [],
	api: ['types'],
	connection: ['types'],
	anchors: ['types', 'utils'],
	utils: ['types', 'anchors'],
	drafts: ['types', 'utils'],
	reader: ['types', 'utils', 'api'],
	guide: ['types', 'utils', 'api'],
	review: ['types', 'utils', 'anchors', 'api', 'connection', 'drafts', 'guide', 'reader'],
	page: ['types', 'utils', 'anchors', 'api', 'connection', 'drafts', 'guide', 'reader', 'review']
};
const PARTS = [...Object.keys(LAYERS), 'components'];

/** The import patterns a part may not use: every part it is not listed as building on. */
function outOfReach(part) {
	return PARTS.filter((other) => other !== part && !LAYERS[part].includes(other)).flatMap((other) => [
		`$lib/${other}`,
		`$lib/${other}/*`
	]);
}

const layerRules = Object.keys(LAYERS).map((part) => ({
	files: [`src/lib/${part}/**`],
	rules: {
		'no-restricted-imports': [
			'error',
			{
				patterns: [
					{
						group: outOfReach(part),
						message: `${part}/ builds only on ${LAYERS[part].join(', ') || 'nothing'}`
					}
				]
			}
		]
	}
}));

// What the page's own code may not do to find an element: a test id is the
// tests' to rename, and an id is page-wide. Elements announce themselves to
// whoever needs them; a selector that cannot be avoided reads a data-role.
const NO_PAGE_LOOKUPS = [
	{
		selector: 'Literal[value=/data-testid/]',
		message: 'Do not find elements by test id: register them, or give them a data-role.'
	},
	{
		selector: 'TemplateElement[value.raw=/data-testid/]',
		message: 'Do not find elements by test id: register them, or give them a data-role.'
	},
	{
		selector: "CallExpression[callee.property.name='getElementById']",
		message: 'Do not find elements by a page-wide id: register them with whoever needs them.'
	}
];

export default tseslint.config(
	// Generated from the server by `pnpm api:types`
	{ ignores: ['src/lib/types/generated/'] },
	eslint.configs.recommended,
	...tseslint.configs.recommended,
	...svelte.configs.recommended,
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: {
			parserOptions: {
				svelteConfig
			}
		}
	},
	{
		files: ['**/*.svelte'],
		languageOptions: {
			parserOptions: {
				parser: tseslint.parser
			}
		}
	},
	{
		// The svelte plugin's base config sets the svelte parser for .svelte.ts files,
		// but typescript-eslint's recommended config overrides it with the TS parser.
		// Re-apply the svelte parser so $state/$derived/$effect runes are parsed correctly.
		files: ['**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: {
			parser: svelte.parser,
			parserOptions: {
				parser: tseslint.parser,
				svelteConfig
			}
		}
	},
	{
		// TypeScript handles no-undef better than eslint for TS/Svelte files
		files: ['**/*.ts', '**/*.svelte'],
		rules: {
			'no-undef': 'off'
		}
	},
	{
		files: ['**/*.svelte'],
		rules: {
			// {@html} is used intentionally with highlight.js (output is escaped)
			'svelte/no-at-html-tags': 'warn',
			// These svelte-ignore comments suppress a11y warnings from the Svelte compiler, not eslint
			'svelte/no-unused-svelte-ignore': 'off'
		}
	},
	...layerRules,
	{
		files: ['src/lib/**'],
		rules: {
			'no-restricted-syntax': ['error', ...NO_PAGE_LOOKUPS]
		}
	},
	{
		ignores: ['node_modules/', 'dist/']
	}
);
