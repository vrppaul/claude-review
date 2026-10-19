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
// A z- utility in a class, behind any variants, its sign and its mark: `z-10`, `md:z-10`, `-z-1`, `!z-10`
const Z_UTILITY = `/${UTILITY_START}z-/`;
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
// Every size is taken off one scale (tokens.css), in markup as in a stylesheet, where stylelint holds the same
// steps: what stands apart, stands in or is set in, and where a thing stands, is one of its steps of Tailwind's
// spacing; words are set at one of its sizes, at that size's own leading, in one of its two weights; a corner is a
// field's or a box's, and a line, a strength or a time a token; and nothing is written as an arbitrary value, a
// token being named instead, as a colour is (`grid-cols-(--cr-…)`)
const ON_THE_SCALE =
	'Take the size off the scale (tokens.css): a spacing step it has, a size and weight of its words, or a token by name.';
// A utility of room or of where a thing stands at a step off the scale or a hairline, behind any variants and its
// sign: `gap-2.5`, `md:pl-3.5`, `-mt-5`, `top-5`, `-translate-y-2.5`, `scroll-mt-5`, `indent-5`, `p-px`; a share
// of what it stands in, `left-1/2`, is a place, no size
const ROOM_OFF_THE_SCALE = `/${UTILITY_START}(p[xytblrse]?|m[xytblrse]?|gap(-[xy])?|space-[xy]|inset(-[xy])?|top|right|bottom|left|start|end|translate-[xy]|scroll-[mp][xytblrse]?|indent)-((?!(0|0\\.5|1|1\\.5|2|3|4|6|8|[0-9]+\\/[0-9]+)${UTILITY_END})[0-9]|px${UTILITY_END})/`;
// A box is sized by a token by name (tokens.css), as a colour is painted
const SIZED_BY_A_TOKEN = 'Size a box by a token by name (tokens.css): w-(--cr-…), min-h-(--cr-…).';
// A width, a height or a basis at a step of Tailwind's own, behind any variants: numbered, `w-12`, `min-h-16`,
// `md:max-h-60`, `size-4`, `basis-24`; named, `max-w-md`, `w-3xs`, `max-w-prose`, `max-w-screen-lg`; or a hairline,
// `w-px`. None, `min-w-0`, a share of what it stands in, `w-1/2`, and the whole of it, `w-full`, `h-screen`, are
// no size
const SIZE_OFF_THE_SCALE = `/${UTILITY_START}(min-|max-)?(w|h|size|basis)-((?!(0|[0-9]+\\/[0-9]+)${UTILITY_END})[0-9]|(px|[2-3]xs|xs|sm|md|lg|xl|[2-7]xl|prose|screen-[a-z0-9]+)${UTILITY_END})/`;
// A value written in place: `grid-cols-[4rem_1fr]`, `w-[26rem]`, `text-[13px]`
const ARBITRARY_VALUE = `/${UTILITY_START}[a-z0-9-]+-\\[/`;
// Words at a size off the scale, with a leading or a spacing of their own beside their size's, or in a weight off
// it: `text-base`, `text-2xl`, `text-sm/6`, `leading-relaxed`, `tracking-wide`, `font-medium`; a colour at a
// strength, `text-primary/80`, is no size of words
const WORDS_OFF_THE_SCALE = `/${UTILITY_START}(text-(base|[2-9]xl)(${UTILITY_END}|\\/)|text-(2xs|xs|sm|lg|xl)\\/|leading-|tracking-|font-(thin|extralight|light|medium|bold|extrabold|black)${UTILITY_END})/`;
// A corner, a line, a ring, a strength or a time at a step of Tailwind's own beside the scale's: `rounded`,
// `rounded-sm`, `rounded-t-lg`, `border-4`, `divide-y-2`, `ring-2`, `outline-offset-2`, `opacity-50`, `duration-300`
const MEASURE_OFF_THE_SCALE = `/${UTILITY_START}(rounded(-(t|r|b|l|s|e|tl|tr|bl|br|ss|se|es|ee))?(-(none|xs|sm|md|lg|xl|[2-4]xl))?${UTILITY_END}|(border(-[xytblrse])?|divide-[xy])-(?!0${UTILITY_END})[0-9]|(ring|outline)(-offset)?-[0-9]|opacity-(?!(0|100)${UTILITY_END})[0-9]|(duration|delay)-[0-9])/`;

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
	// A layer or a scrolling box held in a script's string is handed to a class list all the same
	{ selector: `Literal[value=${Z_UTILITY}]`, message: LAYERED_BY_TOKENS },
	{ selector: `TemplateElement[value.raw=${Z_UTILITY}]`, message: LAYERED_BY_TOKENS },
	{ selector: `Literal[value=${SCROLLING_UTILITY}]`, message: SCROLLS_IN_ITS_OWN_BOX },
	{ selector: `TemplateElement[value.raw=${SCROLLING_UTILITY}]`, message: SCROLLS_IN_ITS_OWN_BOX },
	...inClassLists(COLOUR_UTILITY, PAINTED_BY_TOKENS),
	...inClassLists(SHADOW_UTILITY, PAINTED_BY_TOKENS),
	...inClassLists(STATE_VARIANT, PAINTED_BY_STATE_TOKENS),
	...inClassLists(SCROLLING_UTILITY, SCROLLS_IN_ITS_OWN_BOX),
	...inClassLists(ROOM_OFF_THE_SCALE, ON_THE_SCALE),
	...inClassLists(SIZE_OFF_THE_SCALE, SIZED_BY_A_TOKEN),
	...inClassLists(ARBITRARY_VALUE, ON_THE_SCALE),
	...inClassLists(WORDS_OFF_THE_SCALE, ON_THE_SCALE),
	...inClassLists(MEASURE_OFF_THE_SCALE, ON_THE_SCALE)
];

// Every kind the page draws is drawn by the component library (lib/ui), from the tokens, and none by DaisyUI,
// whose plugin stays for its themes' colours alone: its buttons darkened a dark ground under the pointer, its badges
// counted threads at two sizes, its textarea, checkboxes and spinners stood beside the page's own, and its alert
// said a review could not be opened. A class of any of its components is refused in a class list everywhere, inside
// the library too; and in any string a component holds, as a constant of classes holds them as much as markup does,
// where the class is no word of a sentence: `btn`, `kbd` and `badge` alone, as `<svelte:element this="kbd">` would
// draw a key past the rule on elements below, and any component's variant, `alert-error`, `modal-box`. Tailwind's
// own `table`, `collapse`, `list-…`, `select-…` and `mask-…` share names with DaisyUI's, so only the forms Tailwind
// has not are refused: held against every class DaisyUI 5.5 writes and Tailwind 4.2 lists, the rule refuses no
// class of Tailwind's, and lets through of DaisyUI's only `mask-circle`, which Tailwind has too, the names of its
// states and sizes inside other rules (`is-*`, `lg`), and the classes of other libraries it styles (`pika-*`)
const DRAWN_BY_A_PART =
	"Draw it with a part of lib/ui (a Button, a Field, a Checkbox, a Tag, a Key…), not with a class of DaisyUI's components.";
const DAISY_COMPONENT =
	'/(^|\\s)([^\\s:]+:)*((alert|avatar|badge|breadcrumbs|btn|cally|card|carousel|chat|checkbox|countdown|diff|divider|dock|drawer|dropdown|fab|fieldset|file-input|floating-label|footer|hero|hover-3d|hover-gallery|image-full|indicator|input|join|kbd|label|link|loading|menu|mockup|modal|navbar|progress|radial-progress|radio|range|rating|skeleton|stack|stat|stats|status|step|steps|swap|tab|tabs|text-rotate|textarea|timeline|toast|toggle|tooltip|validator)(-[a-z0-9-]+)?|collapse-(title|content|arrow|plus|open|close)|filter(-reset)?|list(-row|-col-(grow|wrap))?|mask(-(squircle|heart|hexagon(-2)?|decagon|pentagon|diamond|square|star(-2)?|triangle(-[2-4])?|half-[12]))?|row-hover|select(-(bordered|ghost|primary|secondary|accent|neutral|info|success|warning|error|xs|sm|md|lg|xl))?|table-(zebra|pin-rows|pin-cols|xs|sm|md|lg|xl))(\\s|$)/';
const DAISY_COMPONENT_IN_A_STRING =
	'/(^|\\s)((btn|kbd|badge)(-[a-z0-9-]+)?|join-item|(alert|avatar|card|carousel|chat|checkbox|collapse|countdown|divider|dock|drawer|dropdown|fieldset|file-input|hero|indicator|loading|menu|mockup|modal|navbar|radial-progress|radio|rating|skeleton|stat|steps|swap|tabs|textarea|timeline|toast|tooltip|validator)-[a-z0-9-]+)(\\s|$)/';
const NO_DAISY_COMPONENTS = [
	...inClassLists(DAISY_COMPONENT, DRAWN_BY_A_PART),
	{ selector: `Literal[value=${DAISY_COMPONENT_IN_A_STRING}]`, message: DRAWN_BY_A_PART },
	{ selector: `TemplateElement[value.raw=${DAISY_COMPONENT_IN_A_STRING}]`, message: DRAWN_BY_A_PART }
];

// A class of the library's own is its parts' alone, refused outside it in a class list and in any string a component
// holds: the page's copies of a button, drawn with the classes of one, drifted into seven looks
const DRAWN_BY_THE_LIBRARY = "Draw it with a part of lib/ui: a class of the library's own is its parts' alone.";
// A class of the library's own stylesheet
const LIBRARY_CLASS = '/(^|\\s)([^\\s:]+:)*cr-ui-/';
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
const NO_LIBRARY_CLASSES_OUTSIDE = [
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
// are in one string a component holds. A mark whose corner and ground are split over two strings, or over a class
// and a rule of a stylesheet, passes
const A_ROUNDED_CORNER = '/(^|\\s)([^\\s:]+:)*rounded(-\\S+)?(\\s|$)/';
const A_GROUND = '/(^|\\s)([^\\s:]+:)*bg-\\S/';
/** What of an element's start tag holds a pattern among its classes: its class list, written any way, or a class directive. */
function amongItsClasses(pattern) {
	const inTheList = `SvelteLiteral[value=${pattern}], Literal[value=${pattern}], TemplateElement[value.raw=${pattern}]`;
	return `:matches(SvelteAttribute[key.name='class'] :matches(${inTheList}), SvelteDirective[kind='Class'][key.name.name=${pattern}])`;
}
const NO_MARKS_OF_UTILITIES = [
	{
		selector: `SvelteStartTag:has(${amongItsClasses(A_ROUNDED_CORNER)}):has(${amongItsClasses(A_GROUND)})`,
		message: DRAWN_AS_A_MARK
	},
	{ selector: `Literal[value=${A_ROUNDED_CORNER}][value=${A_GROUND}]`, message: DRAWN_AS_A_MARK },
	{ selector: `TemplateElement[value.raw=${A_ROUNDED_CORNER}][value.raw=${A_GROUND}]`, message: DRAWN_AS_A_MARK }
];
// A dot or a cross written as a glyph, in words of markup or in a string, refused inside the library too: drawn at
// the size of the words round it, it drifts with them, as the page's three dots drawn so were 7 px across beside dots
// of 6 and 5
const DRAWN_AS_A_GLYPH = 'Draw a dot with lib/ui Dot, and a cross with <Icon name="cross">, not as a glyph in words.';
const A_GLYPH_MARK = '/[●•⬤×✕✖]/';
const NO_GLYPH_MARKS = [
	{ selector: `SvelteText[value=${A_GLYPH_MARK}]`, message: DRAWN_AS_A_GLYPH },
	{ selector: `Literal[value=${A_GLYPH_MARK}]`, message: DRAWN_AS_A_GLYPH },
	{ selector: `TemplateElement[value.raw=${A_GLYPH_MARK}]`, message: DRAWN_AS_A_GLYPH }
];
const NO_MARKS_OF_ITS_OWN = [
	...NO_GLYPH_MARKS,
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
	'Draw what can be pressed with lib/ui (Button, IconButton, Link, Segment, Chip, Row, ColumnRail, FieldButton, Checkbox), not with an element of its own.';
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
// the library `<svelte:element>` is refused; inside it, a part handed the element it draws (a heading's level, a
// column's landmark) names only elements that are not pressed, by a type no rule here can read
const ELEMENT_AS_WRITTEN = 'Write the element as it is: one handed its kind can be one that is pressed.';
const NO_ELEMENTS_HANDED_THEIR_KIND = [
	{ selector: "SvelteElement[kind='special'][name.name='svelte:element']", message: ELEMENT_AS_WRITTEN }
];
// The controls that are the code's own drawing, drawn with its rows as the code's rows and gutter are the page's
// (page.md): a line's number, which a comment is begun on, and the ways to the lines a gap leaves out, each a
// <button> laid in the table of the code. They are let off the rule that refuses a button, and nothing else is
const PRESSED_IN_THE_CODE = ['src/lib/components/LineGutter.svelte', 'src/lib/components/HunkGap.svelte'];
const BUTTON_IN_THE_LIBRARY = { elements: ['button'], message: PRESSED_IN_THE_LIBRARY };
// A field is drawn by the library (Field, Filter, Checkbox), and nothing outside it draws one: the page drew its
// three fields to write in two ways, with DaisyUI's textarea and with utilities of their own, its two filters on
// two grounds, the field a reply is begun in as a button of main.css, and its checkboxes as DaisyUI's and as a
// chip of main.css
const DRAWN_AS_A_FIELD = 'Draw a field with lib/ui (Field, Filter, Checkbox), not with an element of its own.';
const FIELD_IN_THE_LIBRARY = { elements: ['input', 'textarea', 'select'], message: DRAWN_AS_A_FIELD };
// An image and a link are drawn by the library too: an image pasted into what is said as a Thumbnail, which opens
// it at its full size where it does; a picture of what is new as a Picture; a link as a Link. The page drew its
// thumbnails, the link round one and the news's picture as elements of its own, styled by main.css
const IMAGE_IN_THE_LIBRARY = {
	elements: ['img'],
	message: 'Draw an image with lib/ui Thumbnail or Picture, not with an element of its own.'
};
// What folds is drawn by the library too, a row that folds what is under it or a toggle: the page drew one fold as
// the browser's own <details>, its triangle beside the chevron everything else on the page folds with
const FOLD_IN_THE_LIBRARY = {
	elements: ['details', 'summary'],
	message: 'Fold with lib/ui Row (folded) or FoldToggle, not with an element of its own.'
};
const LINK_IN_THE_LIBRARY = {
	elements: ['a'],
	message: 'Draw a link with lib/ui Link, or a Thumbnail that opens its image, not with an element of its own.'
};
// Nor an element given the part of a field by its role, or made a field by being editable, as a field drawn on a
// <div> would be
const A_FIELD_PART = '/^(textbox|searchbox|combobox|spinbutton|slider)$/';
const NO_FIELDS_OF_ITS_OWN = [
	{
		selector: `SvelteElement[kind='html'] > SvelteStartTag > SvelteAttribute[key.name='role'] SvelteLiteral[value=${A_FIELD_PART}]`,
		message: DRAWN_AS_A_FIELD
	},
	{
		selector: "SvelteElement[kind='html'] > SvelteStartTag > SvelteAttribute[key.name='contenteditable']",
		message: DRAWN_AS_A_FIELD
	}
];
// A heading is drawn by the library (lib/ui Heading), as what it heads says, and nothing outside it draws one: the
// tour's step title and a pane's heading named the same type tokens in two rules, a file's name was a heading drawn
// by a component handed its element, and the story's headings each took their size from utilities of their own
const DRAWN_AS_A_HEADING = 'Draw a heading with lib/ui Heading, as what it heads, not as an element of its own.';
const HEADING_IN_THE_LIBRARY = { elements: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], message: DRAWN_AS_A_HEADING };
// Nor an element that says it is one by its role
const NO_HEADINGS_OF_ITS_OWN = [
	{
		selector:
			"SvelteElement[kind='html'] > SvelteStartTag > SvelteAttribute[key.name='role'] SvelteLiteral[value='heading']",
		message: DRAWN_AS_A_HEADING
	}
];

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
// reach, a card's, a notice's, a pane's and a track's room, a button's and a field's heights — and lays out what
// stands round it itself: the page hung a band's threads past its reach, stood words as far in as a frame's and
// stacked blocks as far apart as a button is tall, each by naming such a token. Named in a class list or in any
// string, or set by a style directive, one is refused outside the library; stylelint refuses one named in a
// stylesheet but the library's
const LAID_OUT_BY_THE_LIBRARY =
	'Lay out round a part of the library with the library: the tokens of its room are its own.';
const A_LIBRARY_ROOM = '/--cr-(edge|band|card|notice|pane|track|button|field)-/';
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

// The colour of what fails is the library's alone — why something could not be done (Failure), the button and the
// icon of what destroys (Button and Icon, of tone danger): the page said what failed in five forms at three sizes,
// and painted its bin by hand. A utility painting with it, at any strength (`text-error/80`), or its token named, is
// refused outside the library in a class list, in any value of markup (a style directive's) and in any string;
// stylelint refuses the token in every stylesheet but the library's
const FAILED_IN_THE_LIBRARY =
	'Say what failed with lib/ui Failure, and draw what destroys as a danger Button or an Icon of tone danger.';
const THE_COLOUR_OF_FAILING = `/${UTILITY_START}${PAINTS}-error(-content)?(\\/|${UTILITY_END})|--color-error/`;
const NO_FAILURES_OF_ITS_OWN = [
	...inClassLists(THE_COLOUR_OF_FAILING, FAILED_IN_THE_LIBRARY),
	{ selector: `SvelteLiteral[value=${THE_COLOUR_OF_FAILING}]`, message: FAILED_IN_THE_LIBRARY },
	{ selector: `Literal[value=${THE_COLOUR_OF_FAILING}]`, message: FAILED_IN_THE_LIBRARY },
	{ selector: `TemplateElement[value.raw=${THE_COLOUR_OF_FAILING}]`, message: FAILED_IN_THE_LIBRARY }
];

// A bar across what it heads is drawn by the library (Bar), and nothing outside it draws one: the page drew the
// review's header and a file section's as two of its own, beside the library's bar of a column, at two rooms. A bar
// drawn anew is a raised ground ruled off above or below, so the raised ground and a rule among the classes of one
// element are refused outside the library
const DRAWN_AS_A_BAR =
	'Draw a bar across what it heads with lib/ui Bar, not with a raised ground and a rule of its own.';
const A_RAISED_GROUND = '/(^|\\s)([^\\s:]+:)*bg-base-200(\\s|$)/';
const A_RULE_ACROSS = '/(^|\\s)([^\\s:]+:)*border-[bty](\\s|$)/';
const NO_BARS_OF_ITS_OWN = [
	{
		selector: `SvelteStartTag:has(${amongItsClasses(A_RAISED_GROUND)}):has(${amongItsClasses(A_RULE_ACROSS)})`,
		message: DRAWN_AS_A_BAR
	}
];

// What a component outside the library is refused: drawing a part of the library its own way
const DRAWN_BY_THE_LIBRARY_ALONE = [
	...NO_DAISY_COMPONENTS,
	...NO_LIBRARY_CLASSES_OUTSIDE,
	...NO_CARDS_OF_ITS_OWN,
	...NO_CODE_BOXES_OF_ITS_OWN,
	...NO_NOTICES_OF_THEIR_OWN,
	...NO_MARKS_OF_ITS_OWN,
	...NO_ROWS_OF_ITS_OWN,
	...NO_FIELDS_OF_ITS_OWN,
	...NO_BARS_OF_ITS_OWN,
	...NO_HEADINGS_OF_ITS_OWN,
	...NO_BANDS_OF_ITS_OWN,
	...NO_FAILURES_OF_ITS_OWN,
	...NO_LAYOUT_ROUND_THE_LIBRARY
];

// The tour lights a place by the name a component marks it with (lib/guide/tour.ts), which svelte-check holds to the
// tour's stops only when it is written through tourStop: it reads no value of a data- attribute. So a name written
// there bare is refused: the words of the attribute, or a string that is its value, either branch of a condition
// or what stands after an `&&`
const NAMED_THROUGH_THE_TOUR =
	"Name a place for the tour with tourStop(…) from lib/guide/tour.ts, which holds the name to the tour's stops.";
const TOUR_ATTRIBUTE = "SvelteAttribute[key.name='data-tour']";
const NO_UNCHECKED_TOUR_NAMES = [
	{ selector: `${TOUR_ATTRIBUTE} > SvelteLiteral`, message: NAMED_THROUGH_THE_TOUR },
	{ selector: `${TOUR_ATTRIBUTE} > SvelteMustacheTag > Literal`, message: NAMED_THROUGH_THE_TOUR },
	{
		selector: `${TOUR_ATTRIBUTE} :matches(ConditionalExpression > Literal.consequent, ConditionalExpression > Literal.alternate, LogicalExpression > Literal.right)`,
		message: NAMED_THROUGH_THE_TOUR
	}
];

/**
 * The syntax refused in a place: what every file of the page is refused, and the lists that place is refused
 * besides. The rule takes one list for a file, the last a block gives it, so a block for a place inside another
 * names again all it still refuses; each such list is written here, from the same parts.
 */
function refusedSyntax(...besides) {
	return ['error', ...NO_NESTED_HELPERS, ...NO_INLINE_STYLING, ...NO_UNCHECKED_TOUR_NAMES, ...besides.flat()];
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
	// Generated from the server by `pnpm api:types`; and the tests, which no linter reads (.claude/rules/tests.md)
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
		// Outside the library a component draws no button, field, image, link or heading of its own either
		files: ['src/**/*.svelte'],
		ignores: ['src/lib/ui/**', ...DRAWING_COMPONENTS, ...PRESSED_IN_THE_CODE],
		rules: {
			'svelte/no-restricted-html-elements': [
				'error',
				SVG_IN_ITS_COMPONENT,
				KBD_IN_ITS_COMPONENT,
				BUTTON_IN_THE_LIBRARY,
				FIELD_IN_THE_LIBRARY,
				IMAGE_IN_THE_LIBRARY,
				LINK_IN_THE_LIBRARY,
				FOLD_IN_THE_LIBRARY,
				HEADING_IN_THE_LIBRARY
			]
		}
	},
	{
		// A control of the code's draws its button, and no field, image, link or heading of its own
		files: PRESSED_IN_THE_CODE,
		rules: {
			'svelte/no-restricted-html-elements': [
				'error',
				SVG_IN_ITS_COMPONENT,
				KBD_IN_ITS_COMPONENT,
				FIELD_IN_THE_LIBRARY,
				IMAGE_IN_THE_LIBRARY,
				LINK_IN_THE_LIBRARY,
				FOLD_IN_THE_LIBRARY,
				HEADING_IN_THE_LIBRARY
			]
		}
	},
	{
		// A component of the page that draws a drawing draws no button, field, image, link or heading of its own
		files: DRAWING_COMPONENTS,
		ignores: ['src/lib/ui/**'],
		rules: {
			'svelte/no-restricted-html-elements': [
				'error',
				KBD_IN_ITS_COMPONENT,
				BUTTON_IN_THE_LIBRARY,
				FIELD_IN_THE_LIBRARY,
				IMAGE_IN_THE_LIBRARY,
				LINK_IN_THE_LIBRARY,
				FOLD_IN_THE_LIBRARY,
				HEADING_IN_THE_LIBRARY
			]
		}
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
		// The library draws its parts with its own classes, and takes no look from outside
		files: ['src/lib/ui/**'],
		rules: {
			'no-restricted-syntax': refusedSyntax(
				NO_PAGE_LOOKUPS,
				NO_CHOOSING,
				NO_DAISY_COMPONENTS,
				TAKES_NO_CLASS,
				NO_GLYPH_MARKS
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
