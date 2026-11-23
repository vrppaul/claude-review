<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorOutdated, anchorShortPlace } from '$lib/anchors/views';
	import PopoverPanel from '$lib/ui/PopoverPanel.svelte';
	import Row from '$lib/ui/Row.svelte';
	import { counted, type CountedWords } from '$lib/utils/words';
	import { keyOf, optionIdOf, type Mentionable, type Mentions } from './mentions.svelte';

	// What the pane is called and headed with, as the button beside the field that opens it says
	const POINT_AT = 'Point at a thread or file';
	// The arrow points down into the field, near where its words start: this far in from the list's left edge, in pixels
	const INTO_THE_FIELD = 20;
	// What the turns under a thread's opening comment are called, counted, where the picker says a thread is live
	const TURNS: CountedWords = { one: 'turn', many: 'turns' };

	/** A kind of thing the list offers, under a heading of its own. */
	interface Section {
		kind: Mentionable['kind'];
		title: string;
	}

	// Threads first, as the review offers them
	const SECTIONS: Section[] = [
		{ kind: 'thread', title: 'Threads' },
		{ kind: 'file', title: 'Files' }
	];

	interface Props {
		mentions: Mentions;
		/** The list's id: the field names it as what it controls. */
		listId: string;
		onTake: (pick: Mentionable) => void;
		/** Put the list away, the keyboard left in the field. */
		onClose: () => void;
	}

	let { mentions, listId, onTake, onClose }: Props = $props();

	// Each candidate with its place in the whole list, which the keys and the field's highlighted option count by
	const numbered = $derived(mentions.candidates.map((pick, index) => ({ pick, index })));

	/** What a thread is in, so the picker says whether it is still live. */
	function threadState(thread: Thread): string {
		if (anchorOutdated(thread.anchor)) return 'outdated';
		if (thread.resolved) return 'resolved';
		if (thread.turns.length > 0) return counted(thread.turns.length, TURNS);
		return '';
	}

	/** A thread's opening words, and the state it is in when it is in one. */
	function threadLine(thread: Thread): string {
		const state = threadState(thread);
		return state ? `${thread.body} · ${state}` : thread.body;
	}

	/** Bring an option into the list's view while it is the one highlighted: the arrow keys move past what the list shows. */
	function showIfHighlighted(option: HTMLElement, highlighted: boolean) {
		if (highlighted) option.scrollIntoView({ block: 'nearest' });
	}
</script>

<!-- A pane as every pane by a control is, headed and put away by its cross, pointing into the field that steers it:
	the keyboard stays in the field, which moves the highlight -->
<PopoverPanel
	role="dialog"
	label={POINT_AT}
	placement="above-start"
	width="along"
	arrow
	arrowOffset={INTO_THE_FIELD}
	head={{ heading: POINT_AT, close: onClose }}
	testId="thread-picker"
>
	<!-- A short list over the conversation, whatever room the window leaves above the field: it scrolls under the
		pane's head. Each option a row on the pane's own room, a kind's name as far in as a row's own room -->
	<div
		id={listId}
		role="listbox"
		aria-label={POINT_AT}
		data-testid="thread-picker-list"
		class="cr-scroller max-h-(--cr-mention-list-tallest) px-3 pb-1"
	>
		{#each SECTIONS as section (section.kind)}
			{@const listed = numbered.filter(({ pick }) => pick.kind === section.kind)}
			{#if listed.length > 0}
				<div role="group" aria-labelledby="{listId}-{section.kind}" data-testid="thread-picker-section">
					<p id="{listId}-{section.kind}" class="cr-faint px-(--cr-list-row-room) pt-2 pb-1 text-xs">
						{section.title}
					</p>
					{#each listed as { pick, index } (keyOf(pick))}
						{@const lit = index === mentions.highlighted}
						<!-- What a thread says, after where it hangs; a file is its path alone -->
						{@const says = pick.kind === 'thread' ? threadLine(pick.thread) : null}
						{#snippet threadSays()}
							{says}
						{/snippet}
						<!-- The option the keys lit is the one of the list the reader is at -->
						<Row
							names="path"
							testId={pick.kind === 'thread' ? 'thread-option' : 'file-option'}
							id={optionIdOf(listId, index)}
							role="option"
							tabindex={-1}
							aria-selected={lit}
							current={lit}
							said={says === null ? undefined : threadSays}
							onclick={() => onTake(pick)}
							{@attach (option: HTMLElement) => showIfHighlighted(option, lit)}
						>
							{#snippet label()}
								{pick.kind === 'thread' ? anchorShortPlace(pick.thread.anchor) : pick.path}
							{/snippet}
						</Row>
					{/each}
				</div>
			{/if}
		{/each}
	</div>
</PopoverPanel>
