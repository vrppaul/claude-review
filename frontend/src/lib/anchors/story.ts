import type { ChapterText, OverviewList, OverviewText, StoryAnchor, StoryBlock } from '$lib/types';
import type { AnchorView } from '$lib/anchors/views';
import { mentionStarts } from '$lib/anchors/token-mentions';
import { fileName } from '$lib/utils/paths';

// What a thread on the story is said to be on, before anything else is named
const STORY = 'Story';
// What stands between the parts of a block's place where there is room
const PLACE_SEPARATOR = ' · ';
// What starts every token of a block, and what parts the names in it
const TOKEN_START = '@story';
const TOKEN_SEPARATOR = ':';
// What stands between a list's word and an item's number in a token
const ITEM_NUMBER_SEPARATOR = '-';
// What carries a block's token on into a longer one: a character an id or a
// path is made of, or a colon or a dot before one. `@story:doubt` sits inside
// `@story:doubt:why`, a chapter's; a colon or a dot ending a sentence does not
const CARRIES_ON = /^(?:[\w-]|[:.][\w-])/;
// The number a person says the first item of a list by, and the place the list holds it at
const FIRST_ITEM_SAID = 1;
const FIRST_ITEM = 0;

// The overview's lines, as the story heads them
const OVERVIEW_LINE_LABELS: Record<OverviewText, string> = { task: 'Task', done: 'Done', doubt: 'Doubt' };
// One item of each of the overview's lists, in a heading and in a token
const ITEM_LABELS: Record<OverviewList, string> = {
	decisions: 'Decision',
	turned_down: 'Turned down',
	later: 'Left for later'
};
const ITEM_TOKENS: Record<OverviewList, string> = {
	decisions: 'decision',
	turned_down: 'turned-down',
	later: 'later'
};
// What a chapter says of itself
const CHAPTER_TEXT_LABELS: Record<ChapterText, string> = { why: 'Why', doubt: 'Where to doubt' };
// A step's reason
const REASON_LABEL = 'Reason';

/** An item's number as a person says it. */
function itemNumber(item: number): number {
	return item - FIRST_ITEM + FIRST_ITEM_SAID;
}

/** What the story heads a block with, above a comment on it and in a thread's own header: "Doubt". */
export function blockLabel(block: StoryBlock): string {
	switch (block.at) {
		case 'overview':
			return OVERVIEW_LINE_LABELS[block.text];
		case 'item':
			return `${ITEM_LABELS[block.list]} ${itemNumber(block.item)}`;
		case 'chapter':
			return CHAPTER_TEXT_LABELS[block.text];
		case 'reason':
			return REASON_LABEL;
	}
}

/** What a block belongs to, named: nothing for the overview's, a chapter by its id, a step by its file and line. */
function holderOf(block: StoryBlock, fileNamed: (path: string) => string): string[] {
	switch (block.at) {
		case 'overview':
		case 'item':
			return [];
		case 'chapter':
			return [block.chapter];
		case 'reason':
			return [`${fileNamed(block.file)}${TOKEN_SEPARATOR}${block.first_line}`];
	}
}

/** What a block is known by: the name its token gives it, which no other block has. */
export function blockKey(block: StoryBlock): string {
	switch (block.at) {
		case 'overview':
			return block.text;
		case 'item':
			return `${ITEM_TOKENS[block.list]}${ITEM_NUMBER_SEPARATOR}${itemNumber(block.item)}`;
		case 'chapter':
			return [block.chapter, block.text].join(TOKEN_SEPARATOR);
		case 'reason':
			return [block.file, block.first_line].join(TOKEN_SEPARATOR);
	}
}

function token({ block }: StoryAnchor): string {
	return [TOKEN_START, blockKey(block)].join(TOKEN_SEPARATOR);
}

/**
 * How a thread on a block of the story's words is named, mentioned and told
 * apart. It was written against the words it quotes; no suggestion replaces a
 * story's words, so one in it replaces nothing.
 */
export const storyAnchorView: AnchorView<StoryAnchor> = {
	label: (anchor) => blockLabel(anchor.block),
	place: (anchor) => [STORY, ...holderOf(anchor.block, (path) => path), blockLabel(anchor.block)].join(PLACE_SEPARATOR),
	shortPlace: (anchor) =>
		[holderOf(anchor.block, fileName).at(0) ?? STORY, blockLabel(anchor.block)].join(PLACE_SEPARATOR),
	token,
	mentionsIn: (text, anchor) => mentionStarts(text, token(anchor), CARRIES_ON),
	sameSpot: (one, other) => blockKey(one.block) === blockKey(other.block),
	writtenAgainst: (anchor) => anchor.quote,
	replaces: () => [],
	placeOf: (anchor) => ({ on: 'story', block: anchor.block })
};

/** One of the overview's three lines, as a block of the story. */
export type OverviewBlock = Extract<StoryBlock, { at: 'overview' }>;

/** The block of one of the overview's three lines. */
export function overviewLine(text: OverviewText): OverviewBlock {
	return { at: 'overview', text };
}

/** A block of the story as the reader asks about it, with the words it says now. */
export function storyAnchor(block: StoryBlock, words: string): StoryAnchor {
	return { kind: 'story', block, quote: [words], outdated: false };
}
