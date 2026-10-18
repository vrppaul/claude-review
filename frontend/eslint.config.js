import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import svelte from 'eslint-plugin-svelte';
import svelteConfig from './svelte.config.js';

// What each part of src/lib may build on. A part importing one it is not
// listed with fails here: nothing reaches up into what is built on it, and
// components, which build on everything, are built on by nothing but
// components.
const LAYERS = {
	// The component library: what the page is drawn with, building on nothing of the page
	ui: [],
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
	reader: ['types', 'utils', 'dom', 'api'],
	guide: ['types', 'api'],
	review: ['types', 'utils', 'dom', 'anchors', 'api', 'drafts', 'guide', 'reader'],
	page: ['types', 'utils', 'api', 'connection', 'drafts', 'reader', 'review']
};
const PARTS = [...Object.keys(LAYERS), 'components'];

// A part of src/lib is named one way: `$lib//page`, `$lib/./page` and
// `$lib/review/../page` reach page/ by a spelling no pattern of a part would
// refuse, so a path with an empty, `.` or `..` step is refused everywhere
const PLAINLY_NAMED = {
	regex: String.raw`^\$lib/(?:[^/]+/)*(?:\.{1,2})?(?:/|$)`,
	message: 'Name a part of $lib plainly, with no empty, . or .. step in the path'
};

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
					},
					PLAINLY_NAMED
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
// body of statements is a helper wherever it is inside another function —
// in a variable, a field, an object, an array, behind a condition or a
// default, handed back as a teardown, or passed straight to a call — and so
// is a function declared there, a function expression of any body, and a
// class. A rune is the one call a body is handed to: an effect's body is the
// effect.
const NESTED_HELPER = 'A helper with logic is a function of the module, not one inside another.';
// What a rune is handed: `$effect(…)`, `$effect.root(…)` and `$derived.by(…)` take a body to run
const RUNE_BODY = 'CallExpression[callee.name=/^\\$/] > *, CallExpression[callee.object.name=/^\\$/] > *';
const NO_NESTED_HELPERS = [
	{
		selector: `:function :matches(ArrowFunctionExpression[expression=false], FunctionExpression, FunctionDeclaration, ClassDeclaration, ClassExpression):not(${RUNE_BODY})`,
		message: NESTED_HELPER
	}
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
// The attribute an element's markup cannot give it, named where code gives it or takes it away: an element a
// library draws, as mermaid draws a diagram's nodes, gets its test id so and is found by none
const SETS_AN_ATTRIBUTE = 'CallExpression[callee.property.name=/^(setAttribute|removeAttribute)$/]';
const NO_PAGE_LOOKUPS = [
	{
		selector: `Literal[value=/data-testid/]:not(${SETS_AN_ATTRIBUTE} > Literal.arguments:first-child)`,
		message: BY_TEST_ID
	},
	{ selector: 'TemplateElement[value.raw=/data-testid/]', message: BY_TEST_ID },
	{ selector: "CallExpression[callee.property.name='getElementById']", message: BY_PAGE_WIDE_ID },
	{ selector: `${SELECTOR_CALL} > Literal[value=${NAMES_AN_ID}]`, message: BY_PAGE_WIDE_ID },
	{
		selector: `${SELECTOR_CALL} > TemplateLiteral > TemplateElement[value.raw=${NAMES_AN_ID}]`,
		message: BY_PAGE_WIDE_ID
	}
];

// How the reader chose to read is written only where they ask to read a way:
// the switch in the header, and Try Story where Story is introduced, through
// the way into Story's `readAsStory`. Taking the reader to what only one view
// draws changes what is on screen and leaves their choice alone
const CHOSEN_BY_THE_READER =
	'Only the switch and Try Story write how the reader chose to read; to bring a view on screen, call showFiles or showStory.';
const NO_CHOOSING = [
	{
		selector: "CallExpression[callee.property.name='choose'][callee.object.property.name='views']",
		message: CHOSEN_BY_THE_READER
	},
	{ selector: "CallExpression[callee.property.name='readAsStory']", message: CHOSEN_BY_THE_READER }
];
// Where the reader asks to read a way: the switch, the news card's Try Story, and the way into Story
const CHOOSERS = [
	'src/lib/components/ViewSwitch.svelte',
	'src/lib/components/GuideCard.svelte',
	'src/lib/review/way-into-story.svelte.ts'
];

// How a component is styled: by classes, and by the stylesheet's tokens. A
// number only the component knows — a dragged width, a depth — reaches the
// stylesheet as a custom property; what lies over what is a layer token,
// never a z- utility, so the stylesheet keeps the one list of layers.
const STYLED_BY_CLASSES = 'Style with a class; hand a number the stylesheet needs to it as style:--name.';
const LAYERED_BY_TOKENS = 'Lay one thing over another with a --cr-layer-* token in the stylesheet, not a z- class.';
// A z- utility in a class, behind any variants and its sign: `z-10`, `md:z-10`, `-z-1`
const Z_UTILITY = '/(^|\\s)([^\\s:]+:)*-?z-/';
// A colour or a shadow is a token too, written once in tokens.css for both
// themes: markup paints with a cr- class or names a token (`text-(--cr-mark)`,
// `bg-base-200`), never with Tailwind's palette (`bg-blue-500`, `text-white`),
// a colour written in place (`text-[#fff]`, `bg-[rgb(…)]`) or a shadow
// utility. Tailwind's utilities for layout, size and type stay.
const PAINTED_BY_TOKENS =
	'Paint with a cr- class or a token (text-(--cr-…)); colours and shadows are written in tokens.css.';
// Where a utility starts in a class list: the start or a space, then any variants (`hover:`, `md:`) and its marks
const UTILITY_START = '(^|\\s)([^\\s:]+:)*!?-?';
// Where one ends: at a space or the list's end, behind the mark that makes it important (`shadow!`)
const UTILITY_END = '!?(\\s|$)';
// The utilities that take a colour
const PAINTS =
	'(bg|text|border(-[xytblrse])?|ring(-offset)?|outline|fill|stroke|from|via|to|decoration|divide|placeholder|caret|accent|inset-ring)';
// A colour of Tailwind's own palette, at any shade, or its black and white. A
// slash in a pattern is escaped: a selector's regex ends at one
const PALETTE = `((slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-[0-9]+|(black|white)(\\/|${UTILITY_END}))`;
// A colour written in place, as an arbitrary value
const RAW_COLOUR = '\\[(#|(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix)\\b)';
const COLOUR_UTILITY = `/${UTILITY_START}${PAINTS}-(${PALETTE}|${RAW_COLOUR})/`;
// Every shadow utility: `shadow`, `shadow-lg`, `drop-shadow-…`, `inset-shadow-…`
const SHADOW_UTILITY = `/${UTILITY_START}(drop-|inset-)?shadow(-|${UTILITY_END})/`;
// A state — under the pointer, pressed, holding the keyboard, the one of a set the reader is at — is drawn by
// the stylesheet with its token (tokens.css), which the palette test holds in both themes: a state variant in
// markup paints with a colour of its own, unseen by that test, as `hover:bg-base-200` did at 1.06:1 in the dark
const PAINTED_BY_STATE_TOKENS =
	'Draw a state in the stylesheet with its token (--cr-hover, --cr-selected, --cr-focus-ring), not with a variant in markup.';
// A variant of a state, the element's own or one it stands in: `hover:`, `focus-visible:`, `aria-pressed:`, `group-hover:`
const STATE_VARIANT =
	'/(^|\\s)([^\\s:]+:)*(hover|focus|focus-visible|focus-within|active|visited|disabled|enabled|checked|open|aria-[^\\s:]+|data-[^\\s:]+|group-[^\\s:]+|peer-[^\\s:]+|has-[^\\s:]+):/';
// What scrolls down the page is a `cr-scroller`, which is the box its contents
// are placed in: words kept for a screen reader are out of the flow, and in a
// scroller made by a utility they stay put while the rest scrolls, on a page
// that grows to hold them. A box that only scrolls sideways — a wide line of
// code — is not one of these
const SCROLLS_IN_ITS_OWN_BOX = 'Make what scrolls a cr-scroller: it is the box its contents are placed in.';
// A utility that makes a box scroll down: `overflow-auto`, `overflow-y-auto`, `overflow-scroll`, `overflow-y-scroll`
const SCROLLING_UTILITY = `/${UTILITY_START}overflow-(y-)?(auto|scroll)${UTILITY_END}/`;

/** Selectors for every way a class list is written in markup, holding a pattern. */
function inClassLists(pattern, message) {
	return [
		{ selector: `SvelteAttribute[key.name='class'] SvelteLiteral[value=${pattern}]`, message },
		{ selector: `SvelteAttribute[key.name='class'] Literal[value=${pattern}]`, message },
		{ selector: `SvelteAttribute[key.name='class'] TemplateElement[value.raw=${pattern}]`, message },
		{ selector: `SvelteDirective[kind='Class'][key.name.name=${pattern}]`, message }
	];
}

const NO_INLINE_STYLING = [
	{ selector: "SvelteAttribute[key.name='style']", message: STYLED_BY_CLASSES },
	{ selector: 'SvelteStyleDirective:not([key.name.name=/^--/])', message: STYLED_BY_CLASSES },
	...inClassLists(Z_UTILITY, LAYERED_BY_TOKENS),
	...inClassLists(COLOUR_UTILITY, PAINTED_BY_TOKENS),
	...inClassLists(SHADOW_UTILITY, PAINTED_BY_TOKENS),
	...inClassLists(STATE_VARIANT, PAINTED_BY_STATE_TOKENS),
	...inClassLists(SCROLLING_UTILITY, SCROLLS_IN_ITS_OWN_BOX)
];

// A button is drawn by the component library (lib/ui), in its tones and sizes, and nothing outside it draws one
// its own way: DaisyUI's buttons darkened a dark ground under the pointer, and the page's own copies of a button
// drifted into seven looks. A class of DaisyUI's buttons is refused in a class list and in any string a component
// holds, a constant of classes as much as markup; a class of the library's own outside it
const DRAWN_BY_THE_LIBRARY =
	'Draw a button with lib/ui (Button, IconButton, Link, Segment), not with classes of its look.';
// DaisyUI's button classes, behind any variants: `btn`, `btn-ghost`, `join`, `join-item`
const DAISY_BUTTON = '/(^|\\s)([^\\s:]+:)*(btn|btn-[a-z]+|join|join-item)(\\s|$)/';
// The same in any string: `join` alone is a word of a sentence as often, and is refused in class lists only
const DAISY_BUTTON_IN_A_STRING = '/(^|\\s)(btn|btn-[a-z]+|join-item)(\\s|$)/';
// A class of the library's own stylesheet
const LIBRARY_CLASS = '/(^|\\s)([^\\s:]+:)*cr-ui-/';
// The library draws its buttons from the tokens, so DaisyUI's are refused inside it too
const NO_DAISY_BUTTONS = [
	...inClassLists(DAISY_BUTTON, DRAWN_BY_THE_LIBRARY),
	{ selector: `Literal[value=${DAISY_BUTTON_IN_A_STRING}]`, message: DRAWN_BY_THE_LIBRARY },
	{ selector: `TemplateElement[value.raw=${DAISY_BUTTON_IN_A_STRING}]`, message: DRAWN_BY_THE_LIBRARY }
];
// A part of the library is handed its test id one way, as `testId`, a prop svelte-check holds every caller to
// give. A part that takes its element's attributes would take a `data-testid` among them too, unseen by any type
const HANDED_ITS_TEST_ID = 'Hand a part of the library its test id as testId, which it lays on what it draws.';
// The parts of the library, by the names the page draws them under
const LIBRARY_PART = '/^(Button|IconButton|Link|Segment|Segmented)$/';
const NO_BUTTONS_OF_ITS_OWN = [
	...NO_DAISY_BUTTONS,
	...inClassLists(LIBRARY_CLASS, DRAWN_BY_THE_LIBRARY),
	{ selector: `Literal[value=${LIBRARY_CLASS}]`, message: DRAWN_BY_THE_LIBRARY },
	{
		selector: `SvelteElement[kind='component'][name.name=${LIBRARY_PART}] > SvelteStartTag > SvelteAttribute[key.name='data-testid']`,
		message: HANDED_ITS_TEST_ID
	}
];

// A part of the library takes no look from outside: what the page needs of one is a variant inside it, with its
// reason. So no part takes a class, by its own name or with the attributes of an element it draws, which it takes
// only with the class left out
const NO_LOOK_FROM_OUTSIDE =
	'A part of the library takes no class: add the look the page needs as a variant inside it.';
// `Omit<…>`, written as a type or as what an interface extends
const OMIT = ":matches(TSTypeReference[typeName.name='Omit'], TSInterfaceHeritage[expression.name='Omit'])";
// The attributes of an element: `HTMLButtonAttributes`, `HTMLAttributes<…>`
const ATTRIBUTES = 'TSTypeReference[typeName.name=/Attributes$/]';
const TAKES_NO_CLASS = [
	{ selector: "TSPropertySignature[key.name='class']", message: NO_LOOK_FROM_OUTSIDE },
	{ selector: "TSPropertySignature[key.value='class']", message: NO_LOOK_FROM_OUTSIDE },
	{ selector: 'TSInterfaceHeritage[expression.name=/Attributes$/]', message: NO_LOOK_FROM_OUTSIDE },
	{
		selector: `${ATTRIBUTES}:not(${OMIT} > TSTypeParameterInstantiation > ${ATTRIBUTES})`,
		message: NO_LOOK_FROM_OUTSIDE
	},
	{
		selector: `${OMIT}:has(${ATTRIBUTES}):not(:has(TSLiteralType > Literal[value='class']))`,
		message: NO_LOOK_FROM_OUTSIDE
	}
];

// Every drawing is drawn in its one component: an icon as a row of ICONS that
// Icon draws by name, the sketch of a story by StorySketch. A review found a
// speech bubble written into another component with numbers of its own,
// beside the same bubble in ICONS
const DRAWN_IN_ITS_COMPONENT =
	'Draw an icon with <Icon name="…">, its drawing a row of ICONS in components/icons.ts; a story sketched is <StorySketch>.';
// The components that write a drawing: Icon, every icon; StorySketch, the sketch of a story
const DRAWING_COMPONENTS = ['src/lib/components/Icon.svelte', 'src/lib/components/StorySketch.svelte'];

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
			// Markup handed to the page whole runs whatever it holds: only the parts listed below, whose markup is escaped, may
			'svelte/no-at-html-tags': 'error',
			// What a button does is written on it: there is no form for it to submit by default
			'svelte/button-has-type': 'error'
		}
	},
	{
		// The lines of a diff, drawn as highlight.js writes them: it escapes the source it is handed, and the
		// marks on changed words (utils/word-diff.ts) are spans put around that escaped text, never inside an escape
		files: ['src/lib/components/RawView.svelte', 'src/lib/components/SplitView.svelte'],
		rules: { 'svelte/no-at-html-tags': 'off' }
	},
	{
		// Markdown as marked writes it: raw HTML in the text is escaped by its renderer, links and images keep
		// only destinations utils/safe-markup.ts lets through, and code is highlighted as the diff is
		files: ['src/lib/components/MarkdownRenderer.svelte'],
		rules: { 'svelte/no-at-html-tags': 'off' }
	},
	{
		// A story's diagram as mermaid draws it (lib/dom/diagram.ts): at its strict level, which no source may
		// change, it cleans the drawing with DOMPurify and writes no handler, and wires none of a source's clicks
		files: ['src/lib/components/StoryDiagram.svelte'],
		rules: { 'svelte/no-at-html-tags': 'off' }
	},
	{
		files: ['**/*.svelte'],
		ignores: DRAWING_COMPONENTS,
		rules: { 'svelte/no-restricted-html-elements': ['error', { elements: ['svg'], message: DRAWN_IN_ITS_COMPONENT }] }
	},
	{
		// The core rule takes a rune's `let` for a plain one; the svelte one knows them
		files: ['**/*.svelte', '**/*.svelte.ts'],
		rules: { 'prefer-const': 'off', 'svelte/prefer-const': 'error' }
	},
	{
		// Everywhere else — the components, the page's entry — a part is named plainly too;
		// each part of src/lib below says so again with what it may not reach
		files: ['src/**'],
		rules: { 'no-restricted-imports': ['error', { patterns: [PLAINLY_NAMED] }] }
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
			'no-restricted-syntax': ['error', ...NO_NESTED_HELPERS, ...NO_INLINE_STYLING, ...NO_BUTTONS_OF_ITS_OWN],
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
			'no-restricted-syntax': [
				'error',
				...NO_NESTED_HELPERS,
				...NO_INLINE_STYLING,
				...NO_PAGE_LOOKUPS,
				...NO_CHOOSING,
				...NO_BUTTONS_OF_ITS_OWN
			]
		}
	},
	{
		files: CHOOSERS,
		rules: {
			'no-restricted-syntax': [
				'error',
				...NO_NESTED_HELPERS,
				...NO_INLINE_STYLING,
				...NO_PAGE_LOOKUPS,
				...NO_BUTTONS_OF_ITS_OWN
			]
		}
	},
	{
		// The library draws its parts with its own classes, and takes no look from outside
		files: ['src/lib/ui/**'],
		rules: {
			'no-restricted-syntax': [
				'error',
				...NO_NESTED_HELPERS,
				...NO_INLINE_STYLING,
				...NO_PAGE_LOOKUPS,
				...NO_CHOOSING,
				...NO_DAISY_BUTTONS,
				...TAKES_NO_CLASS
			]
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
		// Where the rules that read types misread Svelte's own syntax: `= $bindable()` marks a prop the
		// parent may bind, which they take for a default value no caller needs, and `{@render}` of a
		// component's own snippet, which they take for using what a call returning nothing returns
		files: ['**/*.svelte'],
		rules: {
			'@typescript-eslint/no-useless-default-assignment': 'off',
			'@typescript-eslint/no-confusing-void-expression': 'off'
		}
	},
	{
		ignores: ['node_modules/', 'dist/']
	}
);
