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
// Every size is taken off one scale, which tokens.css sets out: a length or a time written as a number is named
// there once and named everywhere else. Nothing is no size in any unit
const A_WRITTEN_SIZE = ['/(?<![\\w.-])(?!0[a-z]+\\b)\\d*\\.?\\d+(px|rem|em|ch|ms|s)\\b/'];
// What stands apart, stands in or is set in stands one of the scale's steps of Tailwind's spacing
const OFF_THE_SCALE = ['/--spacing\\((?!(0|0\\.5|1|1\\.5|2|3|4|6|8)\\))/'];
// Words at one of the scale's sizes, at its own leading, in one of its two weights; and a thing seen whole, gone,
// or at a strength tokens.css names
const THE_SCALES_WORDS = {
	'font-size': ['/^var\\(--(text-[0-9a-z]+|cr-(code|comment)-size)\\)$/'],
	'line-height': ['/^var\\(--(text-[0-9a-z]+--line-height|cr-(code|comment)-leading)\\)$/'],
	'font-weight': ['/^var\\(--font-weight-(normal|semibold)\\)$/'],
	opacity: ['0', '1', '/^var\\(--cr-[a-z-]+\\)$/']
};

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
			// The palette: where the colours and the sizes are written down, the library's rooms some in terms of
			// others, its spacing on the scale's steps
			files: ['src/styles/tokens.css'],
			rules: {
				'color-no-hex': null,
				'function-disallowed-list': null,
				'declaration-property-value-disallowed-list': { '/.*/': OFF_THE_SCALE }
			}
		},
		{
			// The library's stylesheet, which lays a notice's washes, every size of it off the scale
			files: ['src/styles/ui.css'],
			rules: {
				'declaration-property-value-allowed-list': {
					'z-index': A_LAYER,
					'box-shadow': A_SHADOW,
					...THE_SCALES_WORDS
				},
				'declaration-property-value-disallowed-list': { '/.*/': [...A_WRITTEN_SIZE, ...OFF_THE_SCALE] }
			}
		}
	]
};
