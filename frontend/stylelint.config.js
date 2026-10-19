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
// reach, a card's, a notice's and a pane's room, a button's height — and lays out what stands round it itself, so
// no rule outside the library names such a token: the page's band reached back over its frame's room and edge
// with a margin, and page rules hung threads past a band's reach, stood words as far in as a frame's and stacked
// blocks as far apart as a button is tall. Refused in every stylesheet but the library's, and the tokens' own
const A_LIBRARY_ROOM = ['/var\\(--cr-(edge|band|card|notice|pane|button)-/'];

export default {
	rules: {
		'color-no-hex': true,
		'color-named': 'never',
		'function-disallowed-list': ['rgb', 'rgba', 'hsl', 'hsla', 'hwb', 'lab', 'lch', 'oklab', 'oklch', 'color-mix'],
		'declaration-property-value-allowed-list': { 'z-index': A_LAYER, 'box-shadow': A_SHADOW },
		'declaration-property-value-disallowed-list': { '/.*/': [...A_NOTICE_WASH, ...A_LIBRARY_ROOM] },
		'no-duplicate-selectors': true,
		'declaration-no-important': true
	},
	overrides: [
		{
			// The palette: where the colours are written down, and the library's rooms, some in terms of others
			files: ['src/styles/tokens.css'],
			rules: {
				'color-no-hex': null,
				'function-disallowed-list': null,
				'declaration-property-value-disallowed-list': null
			}
		},
		{
			// The library's stylesheet, which lays a notice's washes
			files: ['src/styles/ui.css'],
			rules: { 'declaration-property-value-disallowed-list': null }
		}
	]
};
