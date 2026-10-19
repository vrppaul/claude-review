<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { seenIn } from '$lib/dom/in-sight';
	import PopoverPanel from '$lib/ui/PopoverPanel.svelte';
	import Row from '$lib/ui/Row.svelte';
	import { counted } from '$lib/utils/words';
	import { keyOf, optionIdOf, type Mentionable, type Mentions } from './mentions.svelte';

	// The arrow points down into the field, near where its words start: this far in from the list's left edge, in pixels
	const INTO_THE_FIELD = 20;

	interface Props {
		mentions: Mentions;
		/** The list's id: the field names it as what it controls. */
		listId: string;
		onTake: (pick: Mentionable) => void;
	}

	let { mentions, listId, onTake }: Props = $props();

	/** What a thread is in, so the picker says whether it is still live. */
	function threadState(thread: Thread): string {
		if (thread.anchor.outdated) return 'outdated';
		if (thread.resolved) return 'resolved';
		if (thread.turns.length > 0) return counted(thread.turns.length, { one: 'turn', many: 'turns' });
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

<!-- Threads in the order the diff has them, then files; the keyboard stays in the field, which moves the highlight -->
<PopoverPanel
	id={listId}
	role="listbox"
	label="Threads and files to point at"
	placement="above-start"
	{seenIn}
	width="along"
	arrow
	arrowOffset={INTO_THE_FIELD}
	testId="thread-picker"
>
	<!-- A short list over the conversation, whatever room the window leaves above the field: it scrolls itself.
		Each option a row, lit inside the pane's margin, never to its edge, so the edge the pane's arrow grows from
		keeps the pane's colour -->
	<div class="cr-scroller max-h-60 p-1">
		{#each mentions.candidates as pick, index (keyOf(pick))}
			{@const lit = index === mentions.highlighted}
			<!-- The option the keys lit is the one of the list the reader is at -->
			<Row
				names="path"
				testId={pick.kind === 'thread' ? 'thread-option' : 'file-option'}
				id={optionIdOf(listId, index)}
				role="option"
				tabindex={-1}
				aria-selected={lit}
				current={lit}
				onclick={() => onTake(pick)}
				{@attach (option: HTMLElement) => showIfHighlighted(option, lit)}
			>
				<!-- Where a thread hangs and what it says; or a file's path, and that it is one -->
				{#snippet label()}
					{#if pick.kind === 'thread'}
						<span class="cr-comment-ref">{anchorShortPlace(pick.thread.anchor)}</span>
					{:else}
						<span class="cr-comment-ref">{pick.path}</span>
					{/if}
				{/snippet}
				{#snippet said()}
					{#if pick.kind === 'thread'}
						{threadLine(pick.thread)}
					{:else}
						file
					{/if}
				{/snippet}
			</Row>
		{/each}
	</div>
</PopoverPanel>
