// The stylesheet names the review's tokens and writes none of its own: a
// colour, a layer or a shadow is written down once, in tokens.css, for both
// themes, and named everywhere else — a token on its own, nothing added to
// it. Formatting is Prettier's.
const A_LAYER = ['/^var\\(--cr-layer-[a-z-]+\\)$/'];
const A_SHADOW = ['/^var\\(--cr-shadow-[a-z-]+\\)$/', 'none'];
// The tints a notice's tones stand on, the warning's and the reader's, are laid by the library alone (lib/ui
// NoticeBar, and EdgeFrame's warning): a rule of another stylesheet naming one draws a notice its own way, as
// main.css's .cr-warning-bar drew the bar saying the review cannot be reached beside the library's
const A_NOTICE_TINT = ['/var\\(--cr-(warning|mark)-tint\\)/'];
// The colour of what fails is the library's alone (lib/ui Failure, and a Button and an Icon of tone danger), as
// eslint holds the markup to: a rule of another stylesheet painting with it says what failed its own way
const THE_COLOUR_OF_FAILING = ['/var\\(--color-error/'];
// A part of the library keeps its own room, named after it in tokens.css — an EdgeFrame's edge and room, a band's
// reach, a card's, a notice's, a pane's and a track's room, a button's and a field's heights, a turn's avatar and
// rows — and lays out what stands round it itself, so no rule outside the library names such a token: the page's
// band reached back over its frame's room and edge with a margin, page rules hung threads past a band's reach, stood
// words as far in as a frame's and stacked blocks as far apart as a button is tall, and a thread's spine ended half
// as far down as the field to reply in stood tall. Refused in every stylesheet but the library's, and the tokens' own
const A_LIBRARY_ROOM = ['/var\\(--cr-(edge|band|card|notice|pane|track|button|field|turn)-/'];
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
// Every hue that says whose a thing is or what it means — the reader's, under every name it goes by (its mark, what
// they marked, a control, the keyboard's ring), the agent's, under its name as what is unread, done's, a warning's,
// an error's, what the diff added and removed — is drawn at a step of tokens.css's one ladder of strengths, named as
// that step, as the reader's mark was drawn at five strengths and the agent's at four. A mix naming one with a
// strength written anywhere in it, in any order and any space, is a step of its own; so is a colour made from one
// by the relative syntax. A colour written as numbers holds no alpha but a shadow's and the shade's, so no hue is
// written at a strength of its own that way either
const A_HUE = 'var\\(--(cr-(mark|agent|done|control|focus|unread|add|del)|color-(warning|error))[a-z-]*\\)';
const A_HUE_AT_A_WRITTEN_STRENGTH = [`/color-mix\\((?=.*${A_HUE})(?=.*[\\d.]+%)/`, `/[a-z]+\\(from ${A_HUE}/`];
const AN_ALPHA_WRITTEN = ['/(rgb|hsl|hwb|lab|lch|oklab|oklch)a?\\([^)]*\\//'];
// Every property but those that may hold an alpha of their own: a shadow, and the shade laid behind a modal
const HOLDS_NO_ALPHA = '/^(?!--cr-(shadow-[a-z-]+|shade)$)/';
// A row and a band the keys move hold no motion of their own: the keys outrun it, and two rows stand lit at once
const MOVED_BY_THE_KEYS = { '/\\.cr-ui-(row|band)/': ['/^transition/', '/^animation/'] };
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
// Words at one of the scale's sizes, at that size's leading, in one of its two weights or the weight of the words
// round them, never all three at once in a shorthand; and a thing seen whole, gone, or at a strength tokens.css
// names as one
const THE_SCALES_WORDS = {
	'font-size': ['/^var\\(--(text-(2xs|xs|sm|lg|xl)|cr-(code|comment)-size)\\)$/'],
	'line-height': ['/^var\\(--(text-(2xs|xs|sm|lg|xl)--line-height|cr-(code|comment)-leading)\\)$/'],
	'font-weight': ['/^var\\(--font-weight-(normal|semibold)\\)$/', 'inherit'],
	font: ['inherit'],
	opacity: ['0', '1', '/^var\\(--cr-[a-z-]+-(faint|strength)\\)$/'],
	'stroke-width': A_DRAWN_LINE,
	'stroke-dasharray': A_DRAWN_LINE
};
// What scrolls down the page is a cr-scroller, as eslint holds the markup to: the box its contents are placed in, so
// words kept for a screen reader scroll with them and never stretch the page. Its rule, and the reading area's own,
// say so where they turn this off
const SCROLLS_DOWN = { '/^overflow(-y)?$/': ['/\\b(auto|scroll)\\b/'] };
// A class of the library's stylesheet is the library's to draw: its parts' own, and the three the page's drawings
// and words take from it, the states of what can be pressed, a comment's reading face and what is kept in sight. A
// rule of another stylesheet selecting one would lay a look over a part from outside, so none may
const SELECTORS_OF_THE_LIBRARY = [
	'/\\.cr-(ui-|(pressable|comment-body)(?![\\w-]))/',
	'/\\[data-role=[\'"]?kept-in-sight/'
];
// A comment's reading face is written once, in the library's rule of it (cr-comment-body): another stylesheet naming
// its size or leading writes it again, as a story's prose and its waiting room did
const THE_COMMENT_FACE = ['/var\\(--cr-comment-(size|leading)\\)/'];

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
				...A_NOTICE_TINT,
				...THE_COLOUR_OF_FAILING,
				...THE_COMMENT_FACE,
				...A_LIBRARY_ROOM
			],
			...SCROLLS_DOWN
		},
		'no-duplicate-selectors': true,
		'declaration-no-important': true,
		'selector-disallowed-list': SELECTORS_OF_THE_LIBRARY,
		'rule-selector-property-disallowed-list': MOVED_BY_THE_KEYS
	},
	overrides: [
		{
			// The palette: where the colours, the sizes and the curves are written down, the library's rooms some in
			// terms of others, its spacing on the scale's steps, every hue on the ladder's
			files: ['src/styles/tokens.css'],
			rules: {
				'color-no-hex': null,
				'function-disallowed-list': null,
				'declaration-property-value-disallowed-list': {
					'/.*/': [...OFF_THE_SCALE, ...A_HUE_AT_A_WRITTEN_STRENGTH],
					[HOLDS_NO_ALPHA]: AN_ALPHA_WRITTEN
				}
			}
		},
		{
			// The library's stylesheet, which lays a notice's washes and its parts' rooms, and selects its own classes
			files: ['src/styles/ui.css'],
			rules: {
				'declaration-property-value-disallowed-list': {
					'/.*/': [...A_WRITTEN_SIZE, ...OFF_THE_SCALE, ...THE_STEP_MULTIPLIED],
					...SCROLLS_DOWN
				},
				'selector-disallowed-list': null
			}
		}
	]
};
