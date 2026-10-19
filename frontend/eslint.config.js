import { readdirSync } from 'node:fs';
import { basename } from 'node:path';
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import svelte from 'eslint-plugin-svelte';
import svelteConfig from './svelte.config.js';

// What each part of src/lib may build on. A part importing one it is not
// listed with fails here: nothing reaches up into what is built on it, and
// components, which build on everything, are built on by nothing but
// components.
const LAYERS = {
	// The component library: what the page is drawn with, building on nothing of the page but what the page does to
	// the document, which builds on nothing itself: a pane asks it what of the window the pane is seen in
	ui: ['dom'],
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
// The parts of the library, by the names the page draws them under: every component in its folder, read as the
// config is, so a part added is held as it is written and none is left out of a list kept by hand
const LIBRARY_FOLDER = new URL('./src/lib/ui/', import.meta.url);
const COMPONENT = '.svelte';
const LIBRARY_PARTS = readdirSync(LIBRARY_FOLDER)
	.filter((file) => file.endsWith(COMPONENT))
	.map((file) => basename(file, COMPONENT));
const LIBRARY_PART = `/^(${LIBRARY_PARTS.join('|')})$/`;
const NO_BUTTONS_OF_ITS_OWN = [
	...NO_DAISY_BUTTONS,
	...inClassLists(LIBRARY_CLASS, DRAWN_BY_THE_LIBRARY),
	{ selector: `Literal[value=${LIBRARY_CLASS}]`, message: DRAWN_BY_THE_LIBRARY },
	{
		selector: `SvelteElement[kind='component'][name.name=${LIBRARY_PART}] > SvelteStartTag > SvelteAttribute[key.name='data-testid']`,
		message: HANDED_ITS_TEST_ID
	}
];
// A card is drawn by the library (Card), and nothing outside it draws one its own way: the page drew a thread's
// card, the agent's answer and the facts of a story on its way as three boxes of its own, at two corners, on two
// grounds, with two rooms round what they held, and placed the thread card's tail by a rule reaching into it.
// Their classes are refused in a class list and in any string a component holds
const DRAWN_AS_A_CARD = 'Draw a card with lib/ui Card, in its tone and where it hangs, not with classes of its own.';
// The classes the page drew its cards with
const A_CARD_OF_ITS_OWN = '/(^|\\s)([^\\s:]+:)*(cr-thread-card|cr-answer|cr-wait-facts)(\\s|$)/';
const NO_CARDS_OF_ITS_OWN = [
	...inClassLists(A_CARD_OF_ITS_OWN, DRAWN_AS_A_CARD),
	{ selector: `Literal[value=${A_CARD_OF_ITS_OWN}]`, message: DRAWN_AS_A_CARD },
	{ selector: `TemplateElement[value.raw=${A_CARD_OF_ITS_OWN}]`, message: DRAWN_AS_A_CARD }
];
// Code set apart to read or copy is boxed by the library (CodeBox), on a quiet card, and nothing outside it boxes
// code its own way: the panel's commands and a story's diagram source were two boxes drawn by hand, at 13 and 12
// px, at two corners. So a `pre` given an edge, a corner or a ground of its own in its class list is refused
const BOXED_BY_THE_LIBRARY = 'Set code apart with lib/ui CodeBox, not with an edge, a corner or a ground of its own.';
// A utility that gives an element an edge, a corner or a ground, behind any variants: `border`, `rounded-…`, `bg-…`
const A_BOX_OF_ITS_OWN = '/(^|\\s)([^\\s:]+:)*(border|rounded|bg)(-\\S*)?(\\s|$)/';
// The class list of a `pre`, the element that keeps code's lines as they are written
const CLASS_OF_CODE = "SvelteElement[name.name='pre'] > SvelteStartTag > SvelteAttribute[key.name='class']";
const NO_CODE_BOXES_OF_ITS_OWN = [
	{ selector: `${CLASS_OF_CODE} SvelteLiteral[value=${A_BOX_OF_ITS_OWN}]`, message: BOXED_BY_THE_LIBRARY },
	{ selector: `${CLASS_OF_CODE} Literal[value=${A_BOX_OF_ITS_OWN}]`, message: BOXED_BY_THE_LIBRARY },
	{ selector: `${CLASS_OF_CODE} TemplateElement[value.raw=${A_BOX_OF_ITS_OWN}]`, message: BOXED_BY_THE_LIBRARY }
];
// A notice is drawn by the library (NoticeBar), in its tone, and nothing outside it draws one its own way: beside
// it the page drew by hand the bar saying the review cannot be reached, the one saying it is over, the one in place
// of a part that could not be drawn and a file's notes, from 29 to 48 px tall, their words at two sizes, one of them
// centred. A notice is words on its tone's ground: the grounds of its tones that are washes of a colour — the
// warning's, the reader's softest — are laid by the library alone, so one named in markup or in any string is
// refused, as are the classes the page drew its notices with; stylelint holds every stylesheet but the library's
// to the same. A quiet or a done notice stands on the raised surface every header of the page stands on, which no
// rule here tells from a header's
const DRAWN_AS_A_NOTICE = 'Draw a notice with lib/ui NoticeBar, in its tone, not on a wash or with classes of its own.';
// The washes a notice's tones stand on, and the classes the page drew its notices with, behind any variants
const A_NOTICE_OF_ITS_OWN =
	'/--cr-(warning-tint|mark-soft)\\b|(^|\\s)([^\\s:]+:)*(cr-notice(-[a-z]+)*|cr-warning-bar)(\\s|$)/';
const NO_NOTICES_OF_THEIR_OWN = [
	{ selector: `SvelteLiteral[value=${A_NOTICE_OF_ITS_OWN}]`, message: DRAWN_AS_A_NOTICE },
	{ selector: `SvelteDirective[kind='Class'][key.name.name=${A_NOTICE_OF_ITS_OWN}]`, message: DRAWN_AS_A_NOTICE },
	{ selector: `Literal[value=${A_NOTICE_OF_ITS_OWN}]`, message: DRAWN_AS_A_NOTICE },
	{ selector: `TemplateElement[value.raw=${A_NOTICE_OF_ITS_OWN}]`, message: DRAWN_AS_A_NOTICE }
];

// A mark standing in a line of words is drawn by the library — a tag, a count, a chip, a dot or a key (Tag, Count,
// Chip, Dot, Key) — and nothing outside it draws one its own way: the page drew a tag two ways, an edged word its
// class lowercased and a filled pill, at three heights by the line each stood in; counted threads with DaisyUI's
// badges at two sizes, at the box's corner where a tag had the field's; drew its chips by hand, the cross that
// takes one out of a message a button of its own beside them; its dots as a glyph, as circles of 6 px and of 5,
// one of utilities in the tree and one of its own in a story's contents; its keys as a `kbd` of its own and as
// bare words; and the release the news is of as a chip of main.css, at 12 px beside tags of 11. The classes it drew
// them with are refused in a class list and in any string a component holds
const DRAWN_AS_A_MARK =
	'Draw a tag, a count, a chip, a dot or a key with lib/ui (Tag, Count, Chip, Dot, Key), not with classes of its own.';
// The classes the page drew its marks with
const A_MARK_OF_ITS_OWN =
	'/(^|\\s)([^\\s:]+:)*(cr-tag|cr-pill|cr-severity-[a-z]*|cr-raised-tag|cr-thread-chip(-[a-z]+)?|cr-chip-drop|cr-dot(-[a-z]+)?|cr-contents-dot|cr-guide-hint-dot|cr-guide-key|cr-guide-release)(\\s|$)/';
// A mark drawn anew is round, as a dot or a pill is, and only the library's Dot is drawn round: a corner made round
// by a utility — `rounded-full` on any side or corner, or any radius written in place, `rounded-[100%]` as much as
// `rounded-[999px]` — is refused outside the library, behind any variants. Nothing in markup is round now. The
// page's own round drawings — a thread's avatars, a story's nodes, the cross on the news card's drawing of a pasted
// image — are drawn by main.css, which no rule here reads
const A_ROUND_CORNER = '/(^|\\s)([^\\s:]+:)*rounded(-[a-z]{1,2})?-(full|\\[[^\\]\\s]*\\])(\\s|$)/';
// A mark drawn anew need not be round: a corner made round at any radius on a ground laid by a utility is one,
// `h-1.5 w-1.5 rounded bg-(--cr-unread)` a dot and `rounded bg-(--cr-mark) px-1.5 font-semibold` a count. So a
// rounded utility and a ground utility among the classes of one element are refused outside the library, as they
// are in one string a component holds. A field still draws its own box so, until the library draws fields; a mark
// whose corner and ground are split over two strings, or over a class and a rule of a stylesheet, passes
const A_ROUNDED_CORNER = '/(^|\\s)([^\\s:]+:)*rounded(-\\S+)?(\\s|$)/';
const A_GROUND = '/(^|\\s)([^\\s:]+:)*bg-\\S/';
/** What of an element's start tag holds a pattern among its classes: its class list, written any way, or a class directive. */
function amongItsClasses(pattern) {
	const inTheList = `SvelteLiteral[value=${pattern}], Literal[value=${pattern}], TemplateElement[value.raw=${pattern}]`;
	return `:matches(SvelteAttribute[key.name='class'] :matches(${inTheList}), SvelteDirective[kind='Class'][key.name.name=${pattern}])`;
}
// The start tag of every element but a field, an input or a textarea
const NOT_A_FIELD = 'SvelteElement:not([name.name=/^(input|textarea)$/]) > SvelteStartTag';
const NO_MARKS_OF_UTILITIES = [
	{
		selector: `${NOT_A_FIELD}:has(${amongItsClasses(A_ROUNDED_CORNER)}):has(${amongItsClasses(A_GROUND)})`,
		message: DRAWN_AS_A_MARK
	},
	{ selector: `Literal[value=${A_ROUNDED_CORNER}][value=${A_GROUND}]`, message: DRAWN_AS_A_MARK },
	{ selector: `TemplateElement[value.raw=${A_ROUNDED_CORNER}][value.raw=${A_GROUND}]`, message: DRAWN_AS_A_MARK }
];
// DaisyUI's key and badge, behind any variants and at any size, refused inside the library too, which draws its
// own: `kbd`, `kbd-sm`, `badge`, `badge-primary`. In any string as well: `<svelte:element this="kbd">` would draw a
// key past the rule on elements below, and a badge's classes are as often kept in a constant as written in markup
const DAISY_MARK = '/(^|\\s)([^\\s:]+:)*(kbd|badge)(-[a-z]+)?(\\s|$)/';
// A dot or a cross written as a glyph, in words of markup or in a string: drawn at the size of the words round it,
// it drifts with them, as the page's three dots drawn so were 7 px across beside dots of 6 and 5
const DRAWN_AS_A_GLYPH = 'Draw a dot with lib/ui Dot, and a cross with <Icon name="cross">, not as a glyph in words.';
const A_GLYPH_MARK = '/[●•⬤×✕✖]/';
const NO_GLYPHS_OR_DAISY_MARKS = [
	...inClassLists(DAISY_MARK, DRAWN_AS_A_MARK),
	{ selector: `Literal[value=${DAISY_MARK}]`, message: DRAWN_AS_A_MARK },
	{ selector: `TemplateElement[value.raw=${DAISY_MARK}]`, message: DRAWN_AS_A_MARK },
	{ selector: `SvelteText[value=${A_GLYPH_MARK}]`, message: DRAWN_AS_A_GLYPH },
	{ selector: `Literal[value=${A_GLYPH_MARK}]`, message: DRAWN_AS_A_GLYPH },
	{ selector: `TemplateElement[value.raw=${A_GLYPH_MARK}]`, message: DRAWN_AS_A_GLYPH }
];
const NO_MARKS_OF_ITS_OWN = [
	...NO_GLYPHS_OR_DAISY_MARKS,
	...inClassLists(A_MARK_OF_ITS_OWN, DRAWN_AS_A_MARK),
	{ selector: `Literal[value=${A_MARK_OF_ITS_OWN}]`, message: DRAWN_AS_A_MARK },
	{ selector: `TemplateElement[value.raw=${A_MARK_OF_ITS_OWN}]`, message: DRAWN_AS_A_MARK },
	...inClassLists(A_ROUND_CORNER, DRAWN_AS_A_MARK),
	{ selector: `Literal[value=${A_ROUND_CORNER}]`, message: DRAWN_AS_A_MARK },
	{ selector: `TemplateElement[value.raw=${A_ROUND_CORNER}]`, message: DRAWN_AS_A_MARK },
	...NO_MARKS_OF_UTILITIES
];

// What can be pressed is the library's to draw, a row of a list as much as a button: the page drew its rows
// twelve ways, from 24 to 48 px tall, at three corners. So a component outside the library draws no element that
// can be pressed — no <button>, which a row drawn anew would be (below, with the components that still draw one),
// and no element given the part of one by its role, as a row drawn on a <div> would be — and the classes the page
// drew its rows with are refused in a class list and in any string
const PRESSED_IN_THE_LIBRARY =
	'Draw what can be pressed with lib/ui (Button, IconButton, Link, Segment, Chip, Row, ColumnRail), not with an element of its own.';
// The parts an element can be given that are pressed or picked
const A_PRESSED_PART = '/^(button|link|option|menuitem|menuitemcheckbox|menuitemradio|tab|treeitem|checkbox|switch)$/';
// The classes the page drew its rows, and the rail of a column put away, with; and the row the reader was at
const A_ROW_OF_ITS_OWN =
	'/(^|\\s)([^\\s:]+:)*(cr-tree-row|cr-contents-row|cr-aside-row|cr-option|cr-guide-entry|cr-side-column-rail|cr-current)(\\s|$)/';
// A role handed in by an expression can be the part of one that is pressed, past the rule that reads a role as it
// is written: `<div role={PRESSED}>` is a row drawn on a <div> where PRESSED is 'option'. So outside the library an
// element's role is written as it is. A role in a spread of attributes passes
const ROLE_AS_WRITTEN = 'Write the role of an element as it is: one handed in can be the part of what is pressed.';
const NO_ROWS_OF_ITS_OWN = [
	{
		selector: `SvelteElement[kind='html'] > SvelteStartTag > SvelteAttribute[key.name='role'] SvelteLiteral[value=${A_PRESSED_PART}]`,
		message: PRESSED_IN_THE_LIBRARY
	},
	{
		selector:
			"SvelteElement:not([kind='component']) > SvelteStartTag > SvelteAttribute[key.name='role'] > SvelteMustacheTag",
		message: ROLE_AS_WRITTEN
	},
	...inClassLists(A_ROW_OF_ITS_OWN, PRESSED_IN_THE_LIBRARY),
	{ selector: `Literal[value=${A_ROW_OF_ITS_OWN}]`, message: PRESSED_IN_THE_LIBRARY },
	{ selector: `TemplateElement[value.raw=${A_ROW_OF_ITS_OWN}]`, message: PRESSED_IN_THE_LIBRARY }
];
// An element handed its kind can be one that is pressed, past every rule that reads an element as it is written:
// `<svelte:element this={ELEMENT}>` draws a button where ELEMENT is 'button', and `this="kbd"` a key. So outside
// the library `<svelte:element>` is refused, but in the components handed the element they draw by a prop whose type
// names only elements that are not pressed, which no rule here can read
const ELEMENT_AS_WRITTEN = 'Write the element as it is: one handed its kind can be one that is pressed.';
const NO_ELEMENTS_HANDED_THEIR_KIND = [
	{ selector: "SvelteElement[kind='special'][name.name='svelte:element']", message: ELEMENT_AS_WRITTEN }
];
const HANDED_THEIR_ELEMENT = [
	// A file's name: a heading at the level of where it stands, or plain words where something else heads it
	'src/lib/components/FileTitle.svelte',
	// A column beside what is read: the landmark it is, the tree's aside or a story's contents' nav
	'src/lib/components/SideColumn.svelte'
];
// The components that still draw a <button> of their own, each with the part that is to take it or why it is the
// page's: each is let off the rule that refuses one, and nothing else is
const STILL_PRESSED_BY_HAND = [
	// The field a reply is begun in, drawn as the button that opens it: the library's Field is to draw it
	'src/lib/components/OpenThread.svelte',
	// The line a thread is folded to, which opens it again: the library's Fold is to draw it
	'src/lib/components/FoldedThread.svelte',
	// A line's number, and the ways to the lines a gap leaves out: controls in the code, drawn with its rows
	'src/lib/components/LineGutter.svelte',
	'src/lib/components/HunkGap.svelte'
];
const BUTTON_IN_THE_LIBRARY = { elements: ['button'], message: PRESSED_IN_THE_LIBRARY };

// A block of the story the reader may ask about is banded by the library (Band, stacked by Bands), and nothing
// outside it bands one its own way: the page's band reached back over its frame's room and edge by margins built
// from the frame's tokens, and lay its edge over a warning's. The classes it was drawn and laid out with are
// refused in a class list and in any string a component holds; the tokens of the library's room, however the
// band is drawn anew, below
const DRAWN_AS_A_BAND = 'Band a block the reader may ask about with lib/ui Band, and stack such blocks with Bands.';
// The classes the page drew its bands with, and laid out round them
const A_BAND_OF_ITS_OWN =
	'/(^|\\s)([^\\s:]+:)*(cr-askable|cr-askable-written-under|cr-ask-over-block|cr-askable-hangs|cr-askable-stack|cr-voice-inset)(\\s|$)/';
const NO_BANDS_OF_ITS_OWN = [
	...inClassLists(A_BAND_OF_ITS_OWN, DRAWN_AS_A_BAND),
	{ selector: `Literal[value=${A_BAND_OF_ITS_OWN}]`, message: DRAWN_AS_A_BAND },
	{ selector: `TemplateElement[value.raw=${A_BAND_OF_ITS_OWN}]`, message: DRAWN_AS_A_BAND }
];

// A part of the library keeps its own room, named after it in tokens.css — a frame's edge and room, a band's
// reach, a card's, a notice's and a pane's room, a button's height — and lays out what stands round it itself: the
// page hung a band's threads past its reach, stood words as far in as a frame's and stacked blocks as far apart as
// a button is tall, each by naming such a token. Named in a class list or in any string, or set by a style
// directive, one is refused outside the library; stylelint refuses one named in a stylesheet but the library's
const LAID_OUT_BY_THE_LIBRARY =
	'Lay out round a part of the library with the library: the tokens of its room are its own.';
const A_LIBRARY_ROOM = '/--cr-(edge|band|card|notice|pane|button)-/';
const NO_LAYOUT_ROUND_THE_LIBRARY = [
	...inClassLists(A_LIBRARY_ROOM, LAID_OUT_BY_THE_LIBRARY),
	{ selector: `Literal[value=${A_LIBRARY_ROOM}]`, message: LAID_OUT_BY_THE_LIBRARY },
	{ selector: `TemplateElement[value.raw=${A_LIBRARY_ROOM}]`, message: LAID_OUT_BY_THE_LIBRARY },
	{ selector: `SvelteStyleDirective[key.name.name=${A_LIBRARY_ROOM}]`, message: LAID_OUT_BY_THE_LIBRARY }
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

// What a component outside the library is refused: drawing a part of the library its own way
const DRAWN_BY_THE_LIBRARY_ALONE = [
	...NO_BUTTONS_OF_ITS_OWN,
	...NO_CARDS_OF_ITS_OWN,
	...NO_CODE_BOXES_OF_ITS_OWN,
	...NO_NOTICES_OF_THEIR_OWN,
	...NO_MARKS_OF_ITS_OWN,
	...NO_ROWS_OF_ITS_OWN,
	...NO_BANDS_OF_ITS_OWN,
	...NO_LAYOUT_ROUND_THE_LIBRARY
];

/**
 * The syntax refused in a place: what every file of the page is refused, and the lists that place is refused
 * besides. The rule takes one list for a file, the last a block gives it, so a block for a place inside another
 * names again all it still refuses; each such list is written here, from the same parts.
 */
function refusedSyntax(...besides) {
	return ['error', ...NO_NESTED_HELPERS, ...NO_INLINE_STYLING, ...besides.flat()];
}

// A pane opened from a control is a Popover, which stands by the control; a modal stands over the whole review,
// by none. The modals the page asks in, each with why: the question before stories are turned on, asked on the
// way into Story from whichever control the reader pressed — the switch, Story's introduction, the news, whose
// card goes as it is asked; and a story's diagram at its own size, as large as the window allows, which no pane
// by its button could hold
const MODALS = ['src/lib/components/StoryOptIn.svelte', 'src/lib/components/StoryDiagram.svelte'];
const A_PANE_OF_A_CONTROL =
	'A pane opened from a control is a Popover: a modal (Dialog) is only for what MODALS in eslint.config.js lists, with why.';

// Every drawing is drawn in its one component: an icon as a row of ICONS that
// Icon draws by name, the sketch of a story by StorySketch. A review found a
// speech bubble written into another component with numbers of its own,
// beside the same bubble in ICONS
const DRAWN_IN_ITS_COMPONENT =
	'Draw an icon with <Icon name="…">, its drawing a row of ICONS in ui/icons.ts; a story sketched is <StorySketch>.';
// The components that write a drawing: the library's Icon, every icon; StorySketch, the sketch of a story
const DRAWING_COMPONENTS = ['src/lib/ui/Icon.svelte', 'src/lib/components/StorySketch.svelte'];
const SVG_IN_ITS_COMPONENT = { elements: ['svg'], message: DRAWN_IN_ITS_COMPONENT };
// A key of the keyboard is drawn by the library's Key alone, the one component that writes a `kbd`
const KEY_COMPONENTS = ['src/lib/ui/Key.svelte'];
const KBD_IN_ITS_COMPONENT = { elements: ['kbd'], message: 'Draw a key of the keyboard with lib/ui Key.' };

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
		// A drawing and a key of the keyboard each in its one component, and in no other. The rule takes one list of
		// what it refuses in a file, the last written for it, so each list below names again what it still refuses
		files: ['**/*.svelte'],
		rules: { 'svelte/no-restricted-html-elements': ['error', SVG_IN_ITS_COMPONENT, KBD_IN_ITS_COMPONENT] }
	},
	{
		files: DRAWING_COMPONENTS,
		rules: { 'svelte/no-restricted-html-elements': ['error', KBD_IN_ITS_COMPONENT] }
	},
	{
		files: KEY_COMPONENTS,
		rules: { 'svelte/no-restricted-html-elements': ['error', SVG_IN_ITS_COMPONENT] }
	},
	{
		// Outside the library a component draws no button of its own either, but those still pressed by hand
		files: ['src/**/*.svelte'],
		ignores: ['src/lib/ui/**', ...DRAWING_COMPONENTS, ...STILL_PRESSED_BY_HAND],
		rules: {
			'svelte/no-restricted-html-elements': ['error', SVG_IN_ITS_COMPONENT, KBD_IN_ITS_COMPONENT, BUTTON_IN_THE_LIBRARY]
		}
	},
	{
		// A component of the page that draws a drawing draws no button of its own
		files: DRAWING_COMPONENTS,
		ignores: ['src/lib/ui/**'],
		rules: { 'svelte/no-restricted-html-elements': ['error', KBD_IN_ITS_COMPONENT, BUTTON_IN_THE_LIBRARY] }
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
	{
		// A modal only where MODALS says why: every other component opens its panes by their controls
		files: ['src/lib/components/**'],
		ignores: MODALS,
		rules: {
			'no-restricted-imports': [
				'error',
				{ paths: [{ name: '$lib/ui/Dialog.svelte', message: A_PANE_OF_A_CONTROL }], patterns: [PLAINLY_NAMED] }
			]
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
			'no-restricted-syntax': refusedSyntax(DRAWN_BY_THE_LIBRARY_ALONE, NO_ELEMENTS_HANDED_THEIR_KIND),
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
			'no-restricted-syntax': refusedSyntax(
				NO_PAGE_LOOKUPS,
				NO_CHOOSING,
				DRAWN_BY_THE_LIBRARY_ALONE,
				NO_ELEMENTS_HANDED_THEIR_KIND
			)
		}
	},
	{
		files: CHOOSERS,
		rules: {
			'no-restricted-syntax': refusedSyntax(NO_PAGE_LOOKUPS, DRAWN_BY_THE_LIBRARY_ALONE, NO_ELEMENTS_HANDED_THEIR_KIND)
		}
	},
	{
		// A component handed the element it draws, by a prop that names only elements not pressed, draws it as handed
		files: HANDED_THEIR_ELEMENT,
		rules: { 'no-restricted-syntax': refusedSyntax(NO_PAGE_LOOKUPS, NO_CHOOSING, DRAWN_BY_THE_LIBRARY_ALONE) }
	},
	{
		// The library draws its parts with its own classes, and takes no look from outside
		files: ['src/lib/ui/**'],
		rules: {
			'no-restricted-syntax': refusedSyntax(
				NO_PAGE_LOOKUPS,
				NO_CHOOSING,
				NO_DAISY_BUTTONS,
				TAKES_NO_CLASS,
				NO_GLYPHS_OR_DAISY_MARKS
			)
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
