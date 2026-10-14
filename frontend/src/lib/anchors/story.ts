import type { ChapterText, OverviewList, OverviewText, StoryAnchor, StoryBlock, ToldStep, ToldStory } from '$lib/types';
import type { AnchorView } from '$lib/anchors/views';
import { mentionStarts } from '$lib/anchors/token-mentions';
import { fileName } from '$lib/utils/paths';

// What a thread on the story is said to be on, before anything else is named
const STORY = 'Story';
// What stands between the parts of a block's place where there is room
const PLACE_SEPARATOR = ' · ';
// What starts every token of a block, and what parts the names in it. A
// chapter is named in a token by its id, which the review holds to letters,
// digits, dots, dashes and underscores: no colon, space or slash in it cuts
// `@story:images-kept:why` short or splits it
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

/** Where a block is, where room is short: what it belongs to, or the story itself, then its label: "ch-2 · Why". */
export function blockShortPlace(block: StoryBlock): string {
	return [holderOf(block, fileName).at(0) ?? STORY, blockLabel(block)].join(PLACE_SEPARATOR);
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
 * apart. It was written against the words it quotes, which read as the story
 * said them; no suggestion replaces a story's words, so one in it replaces
 * nothing.
 */
export const storyAnchorView: AnchorView<StoryAnchor> = {
	label: (anchor) => blockLabel(anchor.block),
	place: (anchor) => [STORY, ...holderOf(anchor.block, (path) => path), blockLabel(anchor.block)].join(PLACE_SEPARATOR),
	shortPlace: (anchor) => blockShortPlace(anchor.block),
	token,
	mentionsIn: (text, anchor) => mentionStarts(text, token(anchor), CARRIES_ON),
	sameSpot: (one, other) => blockKey(one.block) === blockKey(other.block),
	writtenAgainst: (anchor) => anchor.quote,
	quoteReads: 'prose',
	replaces: () => [],
	placeOf: (anchor) => ({ on: 'story', block: anchor.block })
};

/** One of the overview's three lines, as a block of the story. */
export type OverviewBlock = Extract<StoryBlock, { at: 'overview' }>;

/** The overview's three lines, and its lists, in the order the story says them. */
export const OVERVIEW_LINES_IN_ORDER: readonly OverviewText[] = ['task', 'done', 'doubt'];
export const OVERVIEW_LISTS_IN_ORDER: readonly OverviewList[] = ['decisions', 'turned_down', 'later'];
/** What a chapter says of itself, in the order the story says it. */
export const CHAPTER_TEXTS_IN_ORDER: readonly ChapterText[] = ['why', 'doubt'];

/** The block of one of the overview's three lines. */
export function overviewLine(text: OverviewText): OverviewBlock {
	return { at: 'overview', text };
}

/** The block of one thing a list of the overview holds, by where it stands in the list. */
export function overviewItem(list: OverviewList, item: number): StoryBlock {
	return { at: 'item', list, item };
}

/** The blocks of everything the overview's lists hold, list after list, in the order the story says them. */
export function overviewItems(overview: ToldStory['overview']): StoryBlock[] {
	return OVERVIEW_LISTS_IN_ORDER.flatMap((list) => overview[list].map((_, item) => overviewItem(list, item)));
}

/** The block of what a chapter says of itself, the chapter by its id. */
export function chapterText(chapter: string, text: ChapterText): StoryBlock {
	return { at: 'chapter', chapter, text };
}

/** The block of a step's reason, the step by its file and the first line it tells. */
export function stepReason(file: string, firstLine: number): StoryBlock {
	return { at: 'reason', file, first_line: firstLine };
}

/**
 * A step's reason where it is a block of the story to ask about: none where
 * the step gives no reason, or tells a file no thread can name.
 */
export function askableReason(step: ToldStep): string | null {
	return step.piece.commentable ? step.reason : null;
}

/** A block of the story as the reader asks about it, with the words it says now. */
export function storyAnchor(block: StoryBlock, words: string): StoryAnchor {
	return { kind: 'story', block, quote: [words], outdated: false };
}
