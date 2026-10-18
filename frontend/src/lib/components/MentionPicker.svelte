<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { counted } from '$lib/utils/words';
	import { keyOf, optionIdOf, type Mentionable, type Mentions } from './mentions.svelte';
	import PopoverPanel from './PopoverPanel.svelte';

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
	arrowOffset={INTO_THE_FIELD}
	data-testid="thread-picker"
	class="right-0"
>
	<div class="cr-scroller max-h-60 p-1">
		{#each mentions.candidates as pick, index (keyOf(pick))}
			{@const lit = index === mentions.highlighted}
			<!-- The option the keys lit is the one of the list the reader is at -->
			<button
				type="button"
				id={optionIdOf(listId, index)}
				role="option"
				tabindex="-1"
				aria-selected={lit}
				data-testid={pick.kind === 'thread' ? 'thread-option' : 'file-option'}
				class={['cr-option cr-pressable', lit && 'cr-current']}
				onclick={() => onTake(pick)}
				{@attach (option: HTMLElement) => showIfHighlighted(option, lit)}
			>
				{#if pick.kind === 'thread'}
					<span class="cr-comment-ref block truncate font-mono text-xs">{anchorShortPlace(pick.thread.anchor)}</span>
					<span class="cr-muted block truncate text-sm">{threadLine(pick.thread)}</span>
				{:else}
					<span class="cr-comment-ref block truncate font-mono text-xs">{pick.path}</span>
					<span class="cr-faint block truncate text-sm">file</span>
				{/if}
			</button>
		{/each}
	</div>
</PopoverPanel>
