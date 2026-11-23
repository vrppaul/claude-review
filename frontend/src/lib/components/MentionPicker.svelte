<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Thread } from '$lib/types';
	import { anchorOutdated, anchorShortPlace } from '$lib/anchors/views';
	import { isComposingText } from '$lib/dom/keyboard';
	import PopoverPanel from '$lib/ui/PopoverPanel.svelte';
	import Row from '$lib/ui/Row.svelte';
	import { counted, type CountedWords } from '$lib/utils/words';
	import { optionIdOf, type Mentionable, type Mentions } from './mentions.svelte';

	// What the pane is called and headed with: what pressing one of its rows does
	const POINT_AT = 'Point at a thread or file';
	// What its list is called, apart from the pane it is in; and each kind it lists, over its own
	const THREADS_AND_FILES = 'Threads and files';
	const THREADS = 'Threads';
	const FILES = 'Files';
	// The arrow points down into the field, near where its words start: this far in from the list's left edge, in pixels
	const INTO_THE_FIELD = 20;
	// What the turns under a thread's opening comment are called, counted, where the picker says a thread is live
	const TURNS: CountedWords = { one: 'turn', many: 'turns' };

	interface Props {
		mentions: Mentions;
		/** The list's id: the field names it as what it controls. */
		listId: string;
		/** The field that steers the list: a press in it is no press outside the list. */
		field: HTMLElement;
		onTake: (pick: Mentionable) => void;
		/** Put the list away by its cross or by Escape, the keyboard back in the field. */
		onClose: () => void;
		/** Put the list away at a press outside it, the keyboard left where the reader pressed. */
		onPressedOutside: () => void;
	}

	let { mentions, listId, field, onTake, onClose, onPressedOutside }: Props = $props();

	let pane = $state<HTMLDivElement>();
	// What names each kind's heading, which its group is labelled by
	const threadsHeading = $derived(`${listId}-threads`);
	const filesHeading = $derived(`${listId}-files`);

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

	/** Escape anywhere in the pane puts it away: in the field, the field answers it itself. */
	function closeOnEscape(event: KeyboardEvent) {
		if (event.key === 'Escape' && !isComposingText(event)) onClose();
	}

	/** A press outside the pane and the field puts the list away. */
	function closeIfOutside(event: PointerEvent) {
		if (!(event.target instanceof Node) || pane?.contains(event.target) || field.contains(event.target)) return;
		onPressedOutside();
	}
</script>

<svelte:document onpointerdown={closeIfOutside} />

<!-- An option of the list, the one the keys lit being the one of the list the reader is at -->
{#snippet option(pick: Mentionable, index: number, label: Snippet, said: Snippet | undefined)}
	{@const lit = index === mentions.highlighted}
	<Row
		names="path"
		testId={pick.kind === 'thread' ? 'thread-option' : 'file-option'}
		id={optionIdOf(listId, index)}
		role="option"
		tabindex={-1}
		aria-selected={lit}
		current={lit}
		{label}
		{said}
		onclick={() => onTake(pick)}
		{@attach (element: HTMLElement) => showIfHighlighted(element, lit)}
	/>
{/snippet}

<!-- A kind's name over its options, as far in as a row's own room -->
{#snippet kind(id: string, title: string)}
	<p {id} role="presentation" class="cr-faint px-(--cr-list-row-room) pt-2 pb-1 text-xs">{title}</p>
{/snippet}

<!-- A pane as every pane by a control is, headed and put away by its cross, pointing into the field that steers it:
	the keyboard stays in the field, which moves the highlight. Threads, then files, in the order the keys count them -->
<PopoverPanel
	bind:pane
	role="dialog"
	label={POINT_AT}
	placement="above-start"
	width="along"
	arrow
	arrowOffset={INTO_THE_FIELD}
	head={{ heading: POINT_AT, close: onClose }}
	steered
	testId="thread-picker"
	onkeydown={closeOnEscape}
>
	<div id={listId} role="listbox" aria-label={THREADS_AND_FILES} data-testid="thread-picker-list" class="px-3 pb-1">
		{#if mentions.threads.length > 0}
			<div role="group" aria-labelledby={threadsHeading} data-testid="thread-picker-threads">
				{@render kind(threadsHeading, THREADS)}
				{#each mentions.threads as { pick, index } (pick.thread.id)}
					{#snippet place()}
						{anchorShortPlace(pick.thread.anchor)}
					{/snippet}
					{#snippet says()}
						{threadLine(pick.thread)}
					{/snippet}
					{@render option(pick, index, place, says)}
				{/each}
			</div>
		{/if}
		{#if mentions.files.length > 0}
			<div role="group" aria-labelledby={filesHeading} data-testid="thread-picker-files">
				{@render kind(filesHeading, FILES)}
				{#each mentions.files as { pick, index } (pick.path)}
					{#snippet path()}
						{pick.path}
					{/snippet}
					{@render option(pick, index, path, undefined)}
				{/each}
			</div>
		{/if}
	</div>
</PopoverPanel>
