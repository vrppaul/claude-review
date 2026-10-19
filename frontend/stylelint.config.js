// The stylesheet names the review's tokens and writes none of its own: a
// colour, a layer or a shadow is written down once, in tokens.css, for both
// themes, and named everywhere else — a token on its own, nothing added to
// it. Formatting is Prettier's.
const A_LAYER = ['/^var\\(--cr-layer-[a-z-]+\\)$/'];
const A_SHADOW = ['/^var\\(--cr-shadow-[a-z-]+\\)$/', 'none'];
// The washes a notice's tones stand on, the warning's and the reader's softest, are laid by the library alone
// (lib/ui NoticeBar, and EdgeFrame's warning): a rule of another stylesheet naming one draws a notice its own way,
// as main.css's .cr-warning-bar drew the bar saying the review cannot be reached beside the library's
const A_NOTICE_WASH = ['/var\\(--cr-(warning-tint|mark-soft)\\)/'];
// The colour of what fails is the library's alone (lib/ui Failure, and a Button and an Icon of tone danger), as
// eslint holds the markup to: a rule of another stylesheet painting with it says what failed its own way
const THE_COLOUR_OF_FAILING = ['/var\\(--color-error/'];
// A part of the library keeps its own room, named after it in tokens.css — an EdgeFrame's edge and room, a band's
// reach, a card's, a notice's, a pane's and a track's room, a button's and a field's heights — and lays out what
// stands round it itself, so no rule outside the library names such a token: the page's band reached back over its
// frame's room and edge with a margin, page rules hung threads past a band's reach, stood words as far in as a
// frame's and stacked blocks as far apart as a button is tall, and a thread's spine ended half as far down as the
// field to reply in stood tall. Refused in every stylesheet but the library's, and the tokens' own
const A_LIBRARY_ROOM = ['/var\\(--cr-(edge|band|card|notice|pane|track|button|field)-/'];
// The functions that write a colour, and the curve a motion eases along: each written once, in tokens.css
const WRITTEN_IN_THE_TOKENS = [
	'rgb',
	'rgba',
	'hsl',
	'hsla',
	'hwb',
	'lab',
	'lch',
	'oklab',
	'oklch',
	'color-mix',
	'cubic-bezier'
];
// Every size is taken off one scale, which tokens.css sets out: a number with a unit, either way up and in any
// case, is named there once and named everywhere else — every unit but those of a turn and of a grid's share,
// which are no size. Nothing is no size in any unit
const A_WRITTEN_SIZE = ['/(?<![\\w.-])-?(?!0[a-z]+\\b)\\d*\\.?\\d+(?!(deg|grad|rad|turn|fr)\\b)[a-z]+\\b/i'];
// And a line of a drawing, which takes its length as a bare number
const A_DRAWN_LINE = ['/^var\\(--cr-[a-z-]+\\)$/'];
// What stands apart, stands in or is set in stands one of the scale's steps of Tailwind's spacing, written as the
// step, never as the step's length multiplied out
const OFF_THE_SCALE = ['/--spacing\\((?!(0|0\\.5|1|1\\.5|2|3|4|6|8)\\))/'];
const THE_STEP_MULTIPLIED = ['/var\\(--spacing\\)/'];
// Words at one of the scale's sizes, at that size's leading, in one of its two weights, never all three at once in
// a shorthand; and a thing seen whole, gone, or at a strength tokens.css names as one
const THE_SCALES_WORDS = {
	'font-size': ['/^var\\(--(text-(2xs|xs|sm|lg|xl)|cr-(code|comment)-size)\\)$/'],
	'line-height': ['/^var\\(--(text-(2xs|xs|sm|lg|xl)--line-height|cr-(code|comment)-leading)\\)$/'],
	'font-weight': ['/^var\\(--font-weight-(normal|semibold)\\)$/'],
	font: ['inherit'],
	opacity: ['0', '1', '/^var\\(--cr-[a-z-]+-(faint|strength)\\)$/'],
	'stroke-width': A_DRAWN_LINE,
	'stroke-dasharray': A_DRAWN_LINE
};
// What scrolls down the page is a cr-scroller, as eslint holds the markup to: the box its contents are placed in, so
// words kept for a screen reader scroll with them and never stretch the page. Its rule, and the reading area's own,
// say so where they turn this off
const SCROLLS_DOWN = { '/^overflow(-y)?$/': ['/\\b(auto|scroll)\\b/'] };

export default {
	rules: {
		'color-no-hex': true,
		'color-named': 'never',
		'function-disallowed-list': WRITTEN_IN_THE_TOKENS,
		'declaration-property-value-allowed-list': { 'z-index': A_LAYER, 'box-shadow': A_SHADOW, ...THE_SCALES_WORDS },
		'declaration-property-value-disallowed-list': {
			'/.*/': [
				...A_WRITTEN_SIZE,
				...OFF_THE_SCALE,
				...THE_STEP_MULTIPLIED,
				...A_NOTICE_WASH,
				...THE_COLOUR_OF_FAILING,
				...A_LIBRARY_ROOM
			],
			...SCROLLS_DOWN
		},
		'no-duplicate-selectors': true,
		'declaration-no-important': true
	},
	overrides: [
		{
			// The palette: where the colours, the sizes and the curves are written down, the library's rooms some in
			// terms of others, its spacing on the scale's steps
			files: ['src/styles/tokens.css'],
			rules: {
				'color-no-hex': null,
				'function-disallowed-list': null,
				'declaration-property-value-disallowed-list': { '/.*/': OFF_THE_SCALE }
			}
		},
		{
			// The library's stylesheet, which lays a notice's washes and its parts' rooms
			files: ['src/styles/ui.css'],
			rules: {
				'declaration-property-value-disallowed-list': {
					'/.*/': [...A_WRITTEN_SIZE, ...OFF_THE_SCALE, ...THE_STEP_MULTIPLIED],
					...SCROLLS_DOWN
				}
			}
		}
	]
};
