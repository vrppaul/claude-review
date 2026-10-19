/**
 * Every word of the review reads on whatever it is drawn on, in both themes,
 * and whatever the pointer is on or the reader is at stands off its ground:
 * the palette's contrasts, worked out from tokens.css as a browser lays its
 * tints, layer by layer in whole channels. A rule of stylelint's, run on
 * tokens.css alone (stylelint.config.js), so a token changed to a colour
 * that does not read is refused at the commit, at the token's own line.
 *
 * What is drawn on what is the lists below, each pair one the stylesheets
 * draw: a reader's need, not a look, so it is held here and not by an eye.
 */
import stylelint from 'stylelint';

const RULE_NAME = 'claude-review/palette-reads';

// WCAG AA for text below 18pt: what every word on the page has to reach, in every state it is seen in
const SMALL_TEXT = 4.5;
// How far what the pointer is on, and the one of a set the reader is at, stand off their ground: in both themes, so
// a dark ground is lit too
const LIT = 1.15;
// What a reader needs to see to know where they are, and where the keyboard is (WCAG 1.4.11, 2.4.13)
const NEEDED = 3;

// The blocks of tokens.css a token is written in: once for both themes, or once in each
const BOTH_THEMES = ':root';
const THEME_BLOCKS = { light: "[data-theme='light']", dark: "[data-theme='dark']" };
const THEMES = Object.keys(THEME_BLOCKS);

// How tokens.css writes a colour: a share of another token over nothing, another token, or channels
const MIXED = /^color-mix\(in srgb, var\((--[a-z0-9-]+)\) ([\d.]+)%, transparent\)$/;
const NAMED = /^var\((--[a-z0-9-]+)\)$/;
const HEX = /^#([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i;
const NUMBER = /[\d.]+/g;
const PERCENT = 100;
const HEX_BASE = 16;
const OPAQUE = 1;

// The sRGB curve, by which a channel's share of light is worked out (WCAG 2.x relative luminance)
const CHANNEL_MAX = 255;
const LINEAR_BELOW = 0.04045;
const LINEAR_SLOPE = 12.92;
const CURVE_OFFSET = 0.055;
const CURVE_SCALE = 1.055;
const CURVE_POWER = 2.4;
const CHANNEL_WEIGHTS = [0.2126, 0.7152, 0.0722];
// What WCAG adds to each luminance before dividing the lighter by the darker: the glare of a screen
const FLARE = 0.05;
// How many decimals a ratio is told in
const RATIO_DECIMALS = 2;

/**
 * What is drawn on what: a text colour, the page's surface under it, and the
 * tints laid over that surface, in order. Each pair is one the stylesheet
 * draws — the token named for the words, on the grounds those words sit on.
 */
const DRAWN = [
	{ said: 'what a thread asks for, on its card', text: '--cr-mark-text', grounds: ['--color-base-200'] },
	{ said: "a comment's place, over the field being written", text: '--cr-mark-text', grounds: ['--color-base-200'] },
	{ said: "a marked row's number", text: '--cr-mark-text', grounds: ['--color-base-100', '--cr-selected'] },
	{
		said: 'the changed-since chip, on a file header',
		text: '--cr-mark-text',
		grounds: ['--color-base-200', '--cr-mark-tint']
	},
	{
		said: "a thread chip, in the reader's message",
		text: '--cr-mark-text',
		grounds: ['--color-base-100', '--cr-mark-tint', '--cr-mark-chip']
	},
	{
		said: 'M on the current row of the tree',
		text: '--cr-status-modified',
		grounds: ['--color-base-100', '--cr-selected']
	},
	{ said: 'a placeholder, in the panel', text: '--cr-placeholder', grounds: ['--color-base-100'] },
	{ said: 'a placeholder, in a field being written', text: '--cr-placeholder', grounds: ['--color-base-200'] },
	{ said: "a placeholder, on a thread's card", text: '--cr-placeholder', grounds: ['--color-base-200'] },
	{
		said: 'a placeholder, in the field a thread offers a reply in',
		text: '--cr-placeholder',
		grounds: ['--color-base-100']
	},
	{ said: "faint words, on a thread's card", text: '--cr-faint', grounds: ['--color-base-200'] },
	{
		said: "the agent's name, and what a thread it raised asks for, on its card",
		text: '--cr-agent',
		grounds: ['--color-base-200']
	},
	{
		said: 'faint words, on the folded line of a thread the agent raised',
		text: '--cr-faint',
		grounds: ['--color-base-100', '--cr-agent-tint']
	},
	{
		said: "the agent's place, on the folded line of a thread it raised",
		text: '--cr-agent',
		grounds: ['--color-base-100', '--cr-agent-tint']
	},
	{ said: "an agent's chip, in the panel", text: '--cr-agent', grounds: ['--color-base-100', '--cr-agent-chip'] },
	{
		said: "an agent's chip in the panel, pointed at",
		text: '--cr-agent',
		grounds: ['--color-base-100', '--cr-agent-chip', '--cr-hover']
	},
	{
		said: "an agent's chip, on the card of its answer or its work",
		text: '--cr-agent',
		grounds: ['--color-base-200', '--cr-agent-chip']
	},
	{
		said: "an agent's chip on the card of its answer or its work, pointed at",
		text: '--cr-agent',
		grounds: ['--color-base-200', '--cr-agent-chip', '--cr-hover']
	},
	{
		said: "a thread chip in the reader's message, pointed at",
		text: '--cr-mark-text',
		grounds: ['--color-base-100', '--cr-mark-tint', '--cr-mark-chip', '--cr-hover']
	},
	{
		said: 'the changed-since chip on a file header, pointed at',
		text: '--cr-mark-text',
		grounds: ['--color-base-200', '--cr-mark-tint', '--cr-hover']
	},
	{
		said: "the other chapters that tell a file, on the header of a story's piece",
		text: '--cr-agent',
		grounds: ['--color-base-200']
	},
	{ said: "a chapter's number, on its node in the contents", text: '--cr-faint', grounds: ['--color-base-200'] },
	{ said: 'what is said of a file in the contents', text: '--cr-faint', grounds: ['--color-base-100'] },
	{ said: 'what a story leaves out, named in its contents', text: '--color-warning', grounds: ['--color-base-200'] },
	{
		said: 'where to doubt a chapter, heading its warning, pointed at',
		text: '--color-warning',
		grounds: ['--color-base-100', '--cr-warning-tint', '--cr-hover']
	},
	{
		said: 'where to doubt a chapter, heading its warning, a thread hanging under it',
		text: '--color-warning',
		grounds: ['--color-base-100', '--cr-warning-tint', '--cr-selected']
	},
	{
		said: 'what to doubt in a chapter, a thread hanging under it',
		text: '--color-base-content',
		grounds: ['--color-base-100', '--cr-warning-tint', '--cr-selected']
	},
	{
		said: 'the check of a part read through, on its node in the contents',
		text: '--cr-done',
		grounds: ['--color-base-200', '--cr-done-soft']
	},
	{ said: "unread, on a thread's card", text: '--cr-unread', grounds: ['--color-base-200'] },
	{ said: 'the one act a pane leads to, on its button', text: '--color-primary-content', grounds: ['--cr-control'] },
	{
		said: 'the one act a pane leads to, on its button pointed at',
		text: '--color-primary-content',
		grounds: ['--cr-control', '--cr-hover-on-fill']
	},
	{
		said: 'an act that loses what was written, on its button',
		text: '--color-error-content',
		grounds: ['--color-error']
	},
	{
		said: 'an act that loses what was written, on its button pointed at',
		text: '--color-error-content',
		grounds: ['--color-error', '--cr-hover-on-fill']
	},
	{ said: 'a filled button, while it cannot be pressed', text: '--cr-muted', grounds: ['--color-base-300'] },
	{
		said: 'the narrowed base picked against, its list open',
		text: '--cr-mark-text',
		grounds: ['--color-base-200', '--cr-mark-tint', '--cr-selected']
	},
	{ said: "a control, on a gap's bar", text: '--cr-control-text', grounds: ['--color-base-200'] },
	{
		said: "a control on a gap's bar, pointed at",
		text: '--cr-control-text',
		grounds: ['--color-base-200', '--cr-hover']
	},
	{ said: "a blocker's tag, on the warning's fill", text: '--color-warning-content', grounds: ['--color-warning'] },
	{ said: "a count of the reader's threads, on their mark", text: '--color-primary-content', grounds: ['--cr-mark'] }
];

// Every colour words are drawn in, by what they say in it
const WORDS = [
	{ said: 'words', text: '--color-base-content' },
	{ said: 'muted words', text: '--cr-muted' },
	{ said: 'faint words', text: '--cr-faint' },
	{ said: 'a line number', text: '--cr-gutter-fg' },
	{ said: "the reader's mark in words", text: '--cr-mark-text' },
	{ said: "the agent's words", text: '--cr-agent' },
	{ said: 'what was added', text: '--cr-add-text' },
	{ said: 'what was taken away', text: '--cr-del-text' },
	{ said: "a modified file's letter", text: '--cr-status-modified' },
	{ said: 'a warning', text: '--color-warning' },
	{ said: 'an error', text: '--color-error' }
];
// The surfaces words stand on: the page's own, and the one a bar, a pane or a card is raised on
const SURFACES = [
	{ said: "the page's ground", surface: '--color-base-100' },
	{ said: 'a raised surface', surface: '--color-base-200' }
];
// What a state lays over a surface under the words of what is in it: nothing at rest, the pointer's light, and
// the reader's mark on the one of a set they are at, which the pointer leaves as it is
const AT_REST_OR_POINTED_AT = [
	{ said: 'at rest', fills: [] },
	{ said: 'pointed at', fills: ['--cr-hover'] }
];
const STATES = [...AT_REST_OR_POINTED_AT, { said: 'selected', fills: ['--cr-selected'] }];
// Every colour of words, on every surface, in every state
const WORDS_IN_EVERY_STATE = WORDS.flatMap(({ said, text }) =>
	SURFACES.flatMap(({ said: on, surface }) =>
		STATES.map(({ said: state, fills }) => ({
			said: `${said}, on ${on}, ${state}`,
			text,
			grounds: [surface, ...fills]
		}))
	)
);
// A segmented control's track, under the words of its segments: muted, and plain on the one pressed
const ON_A_TRACK = ['--cr-muted', '--color-base-content'].flatMap((text) =>
	STATES.map(({ said: state, fills }) => ({
		said: `a segment's words ${text}, on its track, ${state}`,
		text,
		grounds: ['--color-base-300', ...fills]
	}))
);
// A line's number, on the row it numbers, in the row's colour; pointed at, it is lit as whatever can be pressed
const NUMBERED_ROWS = [
	{ row: 'an unchanged row', text: '--cr-gutter-fg', tints: [] },
	{ row: 'an added row', text: '--cr-add-text', tints: ['--cr-add-tint'] },
	{ row: 'a removed row', text: '--cr-del-text', tints: ['--cr-del-tint'] },
	{ row: 'a marked row', text: '--cr-mark-text', tints: ['--cr-selected'] }
];
const LINE_NUMBERS = NUMBERED_ROWS.flatMap(({ row, text, tints }) =>
	AT_REST_OR_POINTED_AT.map(({ said: state, fills }) => ({
		said: `the number of ${row}, ${state}`,
		text,
		grounds: ['--color-base-100', ...tints, ...fills]
	}))
);

// The grounds of a notice that are washes, over the page's: a warning's, and one of the reader's own doing. On each
// stand its words and what can be done about it, a quiet button in the same words, at rest and under the pointer;
// and why doing it failed, in the error's words, which nothing lights
const NOTICE_WASHES = [
	{ said: "a warning's notice", grounds: ['--color-base-100', '--cr-warning-tint'] },
	{ said: "a notice of the reader's own doing", grounds: ['--color-base-100', '--cr-mark-soft'] }
];
const ON_A_NOTICE = NOTICE_WASHES.flatMap(({ said: on, grounds }) => [
	...AT_REST_OR_POINTED_AT.map(({ said: state, fills }) => ({
		said: `the words of ${on} and of a quiet button on it, ${state}`,
		text: '--color-base-content',
		grounds: [...grounds, ...fills]
	})),
	{ said: `why doing something about ${on} failed`, text: '--color-error', grounds }
]);

// Every colour code is highlighted in, by what it colours
const SYNTAX = ['keyword', 'string', 'comment', 'number', 'type', 'function', 'variable', 'meta'];
// Every ground code is drawn on, by the tints laid over the page under it: a
// marked row's tint takes the place of its change's, it does not stack on it;
// the band behind a changed word lies over its row's tint, marked or not
const CODE_ROWS = [
	{ row: 'an unchanged row', tints: [] },
	{ row: 'an added row', tints: ['--cr-add-tint'] },
	{ row: 'a removed row', tints: ['--cr-del-tint'] },
	{ row: 'a marked row', tints: ['--cr-selected'] },
	{ row: 'the band of a word an added row changed', tints: ['--cr-add-tint', '--cr-add-word'] },
	{ row: 'the band of a word a removed row changed', tints: ['--cr-del-tint', '--cr-del-word'] },
	{ row: 'the band of a word a marked added row changed', tints: ['--cr-selected', '--cr-add-word'] },
	{ row: 'the band of a word a marked removed row changed', tints: ['--cr-selected', '--cr-del-word'] }
];
const CODE_DRAWN = SYNTAX.flatMap((colour) =>
	CODE_ROWS.map(({ row, tints }) => ({
		said: `code coloured as ${colour}, on ${row}`,
		text: `--cr-syn-${colour}`,
		grounds: ['--color-base-100', ...tints]
	}))
);

// Every pair of words and what they stand on, held to reading as small text
const READ = [...DRAWN, ...WORDS_IN_EVERY_STATE, ...ON_A_TRACK, ...LINE_NUMBERS, ...CODE_DRAWN, ...ON_A_NOTICE].map(
	({ said, text, grounds }) => ({ said, front: [text], back: grounds, needed: SMALL_TEXT })
);

// A warning's wash on the page, which a chapter's doubt stands on
const WARNING_WASH = ['--color-base-100', '--cr-warning-tint'];
// Every surface a state is drawn on: the page's, a raised one, and a segmented control's track
const STATE_SURFACES = [...SURFACES, { said: 'a track', surface: '--color-base-300' }];
// What the pointer lights, and the light it lays: whatever stands on a surface, and a filled button, whose
// saturated fill moves less under the same light and so takes more of it
const POINTED_AT = [
	...STATE_SURFACES.map(({ said, surface }) => ({ said, surface, light: '--cr-hover' })),
	{ said: "the primary button's own fill", surface: '--cr-control', light: '--cr-hover-on-fill' },
	{ said: 'the fill of a button that loses what was written', surface: '--color-error', light: '--cr-hover-on-fill' }
];
const SELECTED_EDGE = '--cr-selected-edge';
const FOCUS_RING = '--cr-focus-ring';

// Every state held to standing off what it is drawn on: what is in front, laid over what, and how far apart
const SEEN = [
	...POINTED_AT.map(({ said, surface, light }) => ({
		said: `what the pointer is on, against ${said}`,
		front: [surface, light],
		back: [surface],
		needed: LIT
	})),
	...STATE_SURFACES.flatMap(({ said, surface }) => [
		{
			said: `the one of a set the reader is at, against ${said}`,
			front: [surface, '--cr-selected'],
			back: [surface],
			needed: LIT
		},
		{
			said: `the edge of the one of a set the reader is at, against its fill on ${said}`,
			front: [SELECTED_EDGE],
			back: [surface, '--cr-selected'],
			needed: NEEDED
		},
		{
			said: `the edge of the one of a set the reader is at, against ${said}`,
			front: [SELECTED_EDGE],
			back: [surface],
			needed: NEEDED
		},
		{ said: `the ring round what holds the keyboard, on ${said}`, front: [FOCUS_RING], back: [surface], needed: NEEDED }
	]),
	{
		said: "a block a thread hangs under inside a warning, against the warning's wash",
		front: [...WARNING_WASH, '--cr-selected'],
		back: WARNING_WASH,
		needed: LIT
	},
	{
		said: 'the edge of a block a thread hangs under inside a warning, against its fill',
		front: [SELECTED_EDGE],
		back: [...WARNING_WASH, '--cr-selected'],
		needed: NEEDED
	},
	{
		said: "the edge of a block a thread hangs under inside a warning, against the warning's wash",
		front: [SELECTED_EDGE],
		back: WARNING_WASH,
		needed: NEEDED
	},
	...NOTICE_WASHES.flatMap(({ said, grounds }) => [
		{ said: `what the pointer is on, against ${said}`, front: [...grounds, '--cr-hover'], back: grounds, needed: LIT },
		{ said: `the ring round what holds the keyboard, on ${said}`, front: [FOCUS_RING], back: grounds, needed: NEEDED }
	])
];

const CONTRASTS = [...READ, ...SEEN];

const messages = stylelint.utils.ruleMessages(RULE_NAME, {
	unreadable: (said, theme, ratio, needed) =>
		`${said}, in the ${theme} theme: ${ratio.toFixed(RATIO_DECIMALS)}:1, where ${needed}:1 is needed`
});

/** The custom properties a block of tokens.css declares, each by its name. */
function declaredIn(root, selector) {
	const declarations = root.nodes
		.filter((node) => node.type === 'rule' && node.selector === selector)
		.flatMap((rule) => rule.nodes.filter((node) => node.type === 'decl'));
	return new Map(declarations.map((declaration) => [declaration.prop, declaration]));
}

/** The tokens of tokens.css: those written once for both themes, and those written in each theme's own block. */
function tokensOf(root) {
	return {
		bothThemes: declaredIn(root, BOTH_THEMES),
		byTheme: Object.fromEntries(THEMES.map((theme) => [theme, declaredIn(root, THEME_BLOCKS[theme])]))
	};
}

/** Where a token is written for a theme: in the theme's own block, or in the one for both. */
function declarationOf(tokens, token, theme) {
	const declaration = tokens.byTheme[theme].get(token) ?? tokens.bothThemes.get(token);
	if (declaration === undefined) throw new Error(`${RULE_NAME}: ${token} is not in tokens.css`);
	return declaration;
}

/** A token's colour in a theme, following the tokens it is written in terms of: its channels, and how much of what lies under it it covers. */
function paint(tokens, token, theme) {
	const value = declarationOf(tokens, token, theme).value;
	const mixed = MIXED.exec(value);
	if (mixed) return { channels: paint(tokens, mixed[1], theme).channels, alpha: Number(mixed[2]) / PERCENT };
	const named = NAMED.exec(value);
	if (named) return paint(tokens, named[1], theme);
	const hex = HEX.exec(value);
	if (hex) return { channels: hex.slice(1).map((pair) => parseInt(pair, HEX_BASE)), alpha: OPAQUE };
	const [red, green, blue, alpha = OPAQUE] = [...value.matchAll(NUMBER)].map(([number]) => Number(number));
	return { channels: [red, green, blue], alpha };
}

/** A tint laid over a ground, in whole channels, as a browser paints each layer: a pair that reads only before rounding is drawn below it. */
function over(top, ground) {
	return ground.map((channel, channelIndex) =>
		Math.round(top.channels[channelIndex] * top.alpha + channel * (OPAQUE - top.alpha))
	);
}

/** The first layer, with each after it laid over it in order, as the page paints them. */
function laid(tokens, layers, theme) {
	const [first, ...tints] = layers;
	return tints.reduce((under, tint) => over(paint(tokens, tint, theme), under), paint(tokens, first, theme).channels);
}

/** How much light a colour gives off, by WCAG's measure. */
function luminance(channels) {
	return channels
		.map((channel) => channel / CHANNEL_MAX)
		.map((share) =>
			share <= LINEAR_BELOW ? share / LINEAR_SLOPE : ((share + CURVE_OFFSET) / CURVE_SCALE) ** CURVE_POWER
		)
		.reduce((sum, linear, channelIndex) => sum + linear * CHANNEL_WEIGHTS[channelIndex], 0);
}

/** How far two colours stand apart, by WCAG's measure: from 1:1, the same, to 21:1. */
function contrast(one, other) {
	const [lighter, darker] = [luminance(one), luminance(other)].sort((first, second) => second - first);
	return (lighter + FLARE) / (darker + FLARE);
}

/** Every contrast held, in both themes, reported at the line of the token in front where one falls short. */
function reportUnreadable(root, result) {
	const tokens = tokensOf(root);
	for (const theme of THEMES) {
		for (const { said, front, back, needed } of CONTRASTS) {
			const ratio = contrast(laid(tokens, front, theme), laid(tokens, back, theme));
			if (ratio >= needed) continue;
			stylelint.utils.report({
				result,
				ruleName: RULE_NAME,
				message: messages.unreadable(said, theme, ratio, needed),
				node: declarationOf(tokens, front.at(-1), theme)
			});
		}
	}
}

/** The rule as stylelint takes one: on, it reads the whole palette of the sheet it is run on. */
const palette = () => (root, result) => reportUnreadable(root, result);
palette.ruleName = RULE_NAME;
palette.messages = messages;

export default stylelint.createPlugin(RULE_NAME, palette);
