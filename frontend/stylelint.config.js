// The stylesheet names the review's tokens and writes none of its own: a
// colour, a layer or a shadow is written down once, in tokens.css, for both
// themes, and named everywhere else. Formatting is Prettier's.
const BY_TOKEN = ['/var\\(--/', 'none'];

export default {
	rules: {
		'color-no-hex': true,
		'color-named': 'never',
		'function-disallowed-list': ['rgb', 'rgba', 'hsl', 'hsla', 'hwb', 'lab', 'lch', 'oklab', 'oklch', 'color-mix'],
		'declaration-property-value-allowed-list': { 'z-index': BY_TOKEN, 'box-shadow': BY_TOKEN },
		'no-duplicate-selectors': true,
		'declaration-no-important': true
	},
	overrides: [
		{
			// The palette: where the colours are written down
			files: ['src/styles/tokens.css'],
			rules: { 'color-no-hex': null, 'function-disallowed-list': null }
		}
	]
};
