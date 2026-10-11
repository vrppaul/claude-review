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
	// Plain helpers over plain data; nothing of the page in them
	utils: ['types'],
	// What the page does to the document itself: focus, scroll, the tab, and
	// where each file and thread is drawn
	dom: [],
	api: ['types'],
	connection: ['types'],
	anchors: ['types'],
	drafts: ['types', 'utils'],
	reader: ['types', 'utils', 'api'],
	guide: ['types', 'api'],
	review: ['types', 'utils', 'dom', 'anchors', 'api', 'drafts', 'guide', 'reader'],
	page: ['types', 'utils', 'api', 'connection', 'drafts', 'reader', 'review']
};
const PARTS = [...Object.keys(LAYERS), 'components'];

/**
 * The import patterns a part may not use: every part it is not listed as
 * building on, and any path climbing out of its folder, which would reach
 * them without saying so.
 */
function outOfReach(part) {
	const parts = PARTS.filter((other) => other !== part && !LAYERS[part].includes(other)).flatMap((other) => [
		`$lib/${other}`,
		`$lib/${other}/*`
	]);
	return [...parts, '../*'];
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

// Short words that still say what they mean; anything else that short
// abbreviates, and `_` says nothing is kept
const SHORT_WORDS = ['_', 'id', 'at', 'to', 'ok', 'of', 'on', 'by', 'is'];
// A type parameter is a word, as `Kind` or `Choice` is, never one letter
const TYPE_NAME = '^[A-Z][a-z]';

// A helper is a function of its module, with a name and parameters of its
// own, not a closure in the body of another. A one-line lambda — passed to
// a call, or kept to take a listener off again — is still fine; one with a
// body of statements is a helper when it is kept: in a variable, in an
// object, or handed back as a teardown. One passed straight to a call is
// not checked yet: an effect's body is one too, and telling the two apart
// waits for the components to be cleaned.
const NESTED_HELPER = 'A helper with logic is a function of the module, not one inside another.';
const NO_NESTED_HELPERS = [
	{ selector: ':function VariableDeclarator > ArrowFunctionExpression[expression=false]', message: NESTED_HELPER },
	{ selector: ':function VariableDeclarator > FunctionExpression', message: NESTED_HELPER },
	{ selector: ':function FunctionDeclaration', message: NESTED_HELPER },
	{ selector: ':function ReturnStatement > ArrowFunctionExpression[expression=false]', message: NESTED_HELPER },
	{ selector: ':function ReturnStatement > FunctionExpression', message: NESTED_HELPER },
	{ selector: 'ArrowFunctionExpression > ArrowFunctionExpression.body[expression=false]', message: NESTED_HELPER },
	{ selector: ':function Property > FunctionExpression', message: NESTED_HELPER },
	{ selector: ':function Property > ArrowFunctionExpression[expression=false]', message: NESTED_HELPER }
];

// Components written before the rules below, each listed against the rule
// it still breaks. Phases 7 and 8 rework them and empty these lists; nothing
// is added to them, and nothing new is written that would need to be.
const STILL_TO_CLEAN = {
	shortNames: ['FileList', 'KeyboardShortcuts'],
	magicNumbers: ['FileList']
};

/** Where a component still to clean is. */
function componentFiles(names) {
	return names.map((name) => `src/lib/components/${name}.svelte`);
}

// What the page's own code may not do to find an element: a test id is the
// tests' to rename, and an id is page-wide. Elements announce themselves to
// whoever needs them; a selector that cannot be avoided reads a data-role.
const BY_TEST_ID = 'Do not find elements by test id: register them, or give them a data-role.';
const BY_PAGE_WIDE_ID = 'Do not find elements by a page-wide id: register them with whoever needs them.';
// Every call that finds elements by a selector
const SELECTOR_CALL = 'CallExpression[callee.property.name=/^(querySelector(All)?|closest|matches)$/]';
// What in a selector names an id: `#name`, or `[id=…]`
const NAMES_AN_ID = '/#|\\[id\\b/';
const NO_PAGE_LOOKUPS = [
	{ selector: 'Literal[value=/data-testid/]', message: BY_TEST_ID },
	{ selector: 'TemplateElement[value.raw=/data-testid/]', message: BY_TEST_ID },
	{ selector: "CallExpression[callee.property.name='getElementById']", message: BY_PAGE_WIDE_ID },
	{ selector: `${SELECTOR_CALL} > Literal[value=${NAMES_AN_ID}]`, message: BY_PAGE_WIDE_ID },
	{
		selector: `${SELECTOR_CALL} > TemplateLiteral > TemplateElement[value.raw=${NAMES_AN_ID}]`,
		message: BY_PAGE_WIDE_ID
	}
];

// The page makes an HTTP request in one place, which holds every request to the
// server's schema; its session socket is the other way it talks to the server
const OWN_REQUESTS = 'Ask the server through lib/api/request.ts, which holds every request to its schema.';
const REQUEST_CALLERS = ['fetch', 'XMLHttpRequest'].map((name) => ({ name, message: OWN_REQUESTS }));

export default tseslint.config(
	// Generated from the server by `pnpm api:types`; and the tests, held to formatting alone
	{ ignores: ['src/lib/types/generated/', 'tests/'] },
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
		files: ['src/**/*.ts', 'src/**/*.svelte'],
		rules: {
			'id-length': ['error', { min: 3, exceptions: SHORT_WORDS, properties: 'never' }],
			// id-length passes over type parameters; a type has a name, as a value does
			'@typescript-eslint/naming-convention': [
				'error',
				{ selector: 'typeParameter', format: ['PascalCase'], custom: { regex: TYPE_NAME, match: true } }
			],
			'no-restricted-syntax': ['error', ...NO_NESTED_HELPERS],
			'max-lines': ['error', { max: 300, skipBlankLines: true, skipComments: true }],
			// A switch over every kind of a union is one decision, not one per kind
			complexity: ['error', { max: 10, variant: 'modified' }]
		}
	},
	{
		files: ['src/**/*.ts', 'src/**/*.svelte'],
		ignores: componentFiles(STILL_TO_CLEAN.magicNumbers),
		rules: {
			'@typescript-eslint/no-magic-numbers': [
				'error',
				{
					ignore: [0, 1, -1],
					ignoreArrayIndexes: true,
					ignoreDefaultValues: true,
					ignoreEnums: true,
					ignoreNumericLiteralTypes: true,
					ignoreReadonlyClassProperties: true,
					ignoreTypeIndexes: true
				}
			]
		}
	},
	{
		files: ['src/lib/**'],
		rules: {
			'no-restricted-syntax': ['error', ...NO_NESTED_HELPERS, ...NO_PAGE_LOOKUPS]
		}
	},
	{
		files: ['src/**/*.ts', 'src/**/*.svelte'],
		ignores: ['src/lib/api/request.ts'],
		rules: { 'no-restricted-globals': ['error', ...REQUEST_CALLERS] }
	},
	{ files: componentFiles(STILL_TO_CLEAN.shortNames), rules: { 'id-length': 'off' } },
	{
		ignores: ['node_modules/', 'dist/']
	}
);
