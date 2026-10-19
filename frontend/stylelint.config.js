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
// A part of the library keeps its own room, named after it in tokens.css — an EdgeFrame's edge and room, a band's
// reach, a card's, a notice's and a pane's room, a button's height — and no rule outside the library takes that
// back with a margin: the page's band reached back over its frame's room and edge so, and lay its edge over a
// warning's. A margin naming such a token with a minus, `calc(-1 * …)`, `… * -1` or `… - …`, is refused in every
// stylesheet but the library's: a minus no other follows, as one does in the `--` a token's name begins with
const A_LIBRARY_ROOM_TAKEN_BACK = [
	'/^(?=.*var\\(--cr-(edge|band|card|notice|pane|button)-)(?=.*(\\(\\s*-(?!-)|\\*\\s*-(?!-)|\\s-\\s))/'
];

export default {
	rules: {
		'color-no-hex': true,
		'color-named': 'never',
		'function-disallowed-list': ['rgb', 'rgba', 'hsl', 'hsla', 'hwb', 'lab', 'lch', 'oklab', 'oklch', 'color-mix'],
		'declaration-property-value-allowed-list': { 'z-index': A_LAYER, 'box-shadow': A_SHADOW },
		'declaration-property-value-disallowed-list': {
			'/.*/': A_NOTICE_WASH,
			'/^margin/': A_LIBRARY_ROOM_TAKEN_BACK
		},
		'no-duplicate-selectors': true,
		'declaration-no-important': true
	},
	overrides: [
		{
			// The palette: where the colours are written down
			files: ['src/styles/tokens.css'],
			rules: { 'color-no-hex': null, 'function-disallowed-list': null }
		},
		{
			// The library's stylesheet, which lays a notice's washes
			files: ['src/styles/ui.css'],
			rules: { 'declaration-property-value-disallowed-list': null }
		}
	]
};
