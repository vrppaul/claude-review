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
	anchors: ['types', 'utils'],
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
// body of statements is a helper wherever it is: in a variable, in an
// object, handed back as a teardown, or passed straight to a call. A rune
// is the one call a body is handed to: an effect's body is the effect.
const NESTED_HELPER = 'A helper with logic is a function of the module, not one inside another.';
// A call that is not a rune's — `$effect(…)`, `$effect.root(…)` and `$derived.by(…)` take a body to run
const NOT_A_RUNE = ':not([callee.name=/^\\$/]):not([callee.object.name=/^\\$/])';
const NO_NESTED_HELPERS = [
	{ selector: ':function VariableDeclarator > ArrowFunctionExpression[expression=false]', message: NESTED_HELPER },
	{ selector: ':function VariableDeclarator > FunctionExpression', message: NESTED_HELPER },
	{ selector: ':function FunctionDeclaration', message: NESTED_HELPER },
	{ selector: ':function ReturnStatement > ArrowFunctionExpression[expression=false]', message: NESTED_HELPER },
	{ selector: ':function ReturnStatement > FunctionExpression', message: NESTED_HELPER },
	{ selector: 'ArrowFunctionExpression > ArrowFunctionExpression.body[expression=false]', message: NESTED_HELPER },
	{ selector: ':function Property > FunctionExpression', message: NESTED_HELPER },
	{ selector: ':function Property > ArrowFunctionExpression[expression=false]', message: NESTED_HELPER },
	{
		selector: `:function CallExpression${NOT_A_RUNE} > ArrowFunctionExpression[expression=false]`,
		message: NESTED_HELPER
	},
	{ selector: `:function CallExpression${NOT_A_RUNE} > FunctionExpression`, message: NESTED_HELPER },
	{ selector: ':function NewExpression > ArrowFunctionExpression[expression=false]', message: NESTED_HELPER },
	{ selector: ':function NewExpression > FunctionExpression', message: NESTED_HELPER }
];

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

// How a component is styled: by classes, and by the stylesheet's tokens. A
// number only the component knows — a dragged width, a depth — reaches the
// stylesheet as a custom property; what lies over what is a layer token,
// never a z- utility, so the stylesheet keeps the one list of layers.
const STYLED_BY_CLASSES = 'Style with a class; hand a number the stylesheet needs to it as style:--name.';
const LAYERED_BY_TOKENS = 'Lay one thing over another with a --cr-layer-* token in the stylesheet, not a z- class.';
// A z- utility in a class, behind any variants and its sign: `z-10`, `md:z-10`, `-z-1`
const Z_UTILITY = '/(^|\\s)([^\\s:]+:)*-?z-/';
const NO_INLINE_STYLING = [
	{ selector: "SvelteAttribute[key.name='style']", message: STYLED_BY_CLASSES },
	{ selector: 'SvelteStyleDirective:not([key.name.name=/^--/])', message: STYLED_BY_CLASSES },
	{ selector: `SvelteAttribute[key.name='class'] SvelteLiteral[value=${Z_UTILITY}]`, message: LAYERED_BY_TOKENS },
	{ selector: `SvelteAttribute[key.name='class'] Literal[value=${Z_UTILITY}]`, message: LAYERED_BY_TOKENS },
	{ selector: `SvelteAttribute[key.name='class'] TemplateElement[value.raw=${Z_UTILITY}]`, message: LAYERED_BY_TOKENS },
	{ selector: `SvelteDirective[kind='Class'][key.name.name=${Z_UTILITY}]`, message: LAYERED_BY_TOKENS }
];

// The page makes an HTTP request in one place, which holds every request to the
// server's schema; its session socket is the other way it talks to the server
const OWN_REQUESTS = 'Ask the server through lib/api/request.ts, which holds every request to its schema.';
const REQUEST_CALLERS = ['fetch', 'XMLHttpRequest'].map((name) => ({ name, message: OWN_REQUESTS }));

export default tseslint.config(
	// Generated from the server by `pnpm api:types`; and the tests, held to formatting alone
	{ ignores: ['src/lib/types/generated/', 'tests/'] },
	eslint.configs.recommended,
	...tseslint.configs.strictTypeChecked,
	...svelte.configs.recommended,
	{
		// The rules that read types read them from the page's own TypeScript program
		files: ['src/**/*.ts', 'src/**/*.svelte'],
		languageOptions: {
			parserOptions: { projectService: true, extraFileExtensions: ['.svelte'], tsconfigRootDir: import.meta.dirname }
		}
	},
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
			// What a button does is written on it: there is no form for it to submit by default
			'svelte/button-has-type': 'error'
		}
	},
	{
		// The core rule takes a rune's `let` for a plain one; the svelte one knows them
		files: ['**/*.svelte', '**/*.svelte.ts'],
		rules: { 'prefer-const': 'off', 'svelte/prefer-const': 'error' }
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
			'no-restricted-syntax': ['error', ...NO_NESTED_HELPERS, ...NO_INLINE_STYLING],
			// A function an interface asks for is a property: a method's parameters are compared
			// loosely, so a value that takes only one kind could stand where every kind is passed
			'@typescript-eslint/method-signature-style': ['error', 'property'],
			// A number has one way to be written into text; anything else — an object, a maybe-missing
			// value, a yes or no — is said on purpose, or it would come out as [object Object] or undefined
			'@typescript-eslint/restrict-template-expressions': [
				'error',
				{
					allowAny: false,
					allowBoolean: false,
					allowNever: false,
					allowNullish: false,
					allowNumber: true,
					allowRegExp: false
				}
			],
			// A handler is one expression here — a body of statements would be a helper of its own —
			// and what it hands back is nobody's to read
			'@typescript-eslint/no-confusing-void-expression': ['error', { ignoreArrowShorthand: true }],
			'max-lines': ['error', { max: 300, skipBlankLines: true, skipComments: true }],
			// A switch over every kind of a union is one decision, not one per kind
			complexity: ['error', { max: 10, variant: 'modified' }],
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
			'no-restricted-syntax': ['error', ...NO_NESTED_HELPERS, ...NO_INLINE_STYLING, ...NO_PAGE_LOOKUPS]
		}
	},
	{
		files: ['src/**/*.ts', 'src/**/*.svelte'],
		ignores: ['src/lib/api/request.ts'],
		rules: { 'no-restricted-globals': ['error', ...REQUEST_CALLERS] }
	},
	{
		// The one place the page takes the server's JSON to be the shape its schema names: both are
		// generated from that schema and ship together, and replies are not checked as they arrive
		files: ['src/lib/api/request.ts'],
		rules: { '@typescript-eslint/no-unsafe-return': 'off' }
	},
	{
		// What the rules that read types cannot see in a component. Their TypeScript program reads
		// every .svelte import through Svelte's own catch-all declaration, which says nothing of a
		// component's props (a callback handed to a child takes any) or of what its module script
		// exports; it does not narrow inside {:else}, types a <svelte:window> handler's event as any,
		// takes `= $bindable()` for a default value, and reads `{@render}` of a snippet as using what a
		// call that returns nothing returns. svelte-check, which reads components as Svelte does, holds
		// their types.
		files: ['**/*.svelte'],
		rules: {
			'@typescript-eslint/no-unsafe-argument': 'off',
			'@typescript-eslint/no-unsafe-assignment': 'off',
			'@typescript-eslint/no-unsafe-call': 'off',
			'@typescript-eslint/no-unsafe-member-access': 'off',
			'@typescript-eslint/no-unsafe-return': 'off',
			'@typescript-eslint/no-useless-default-assignment': 'off',
			'@typescript-eslint/no-confusing-void-expression': 'off'
		}
	},
	{
		ignores: ['node_modules/', 'dist/']
	}
);
