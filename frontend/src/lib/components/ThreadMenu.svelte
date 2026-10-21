<script lang="ts">
	import type { Thread } from '$lib/types';
	import { blockKey } from '$lib/anchors/story';
	import { threadPlaceOf } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { OVERVIEW_PART } from '$lib/review/story-keys';
	import Confirmation from '$lib/ui/Confirmation.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import Menu from '$lib/ui/Menu.svelte';
	import MenuItem from '$lib/ui/MenuItem.svelte';
	import Popover from '$lib/ui/Popover.svelte';
	import { placeKey } from '$lib/utils/line-places';
	import { counted, type CountedWords } from '$lib/utils/words';

	// What the menu's control and its pane are called, said to whoever cannot see the dots
	const MENU = 'Edit or delete';
	const MENU_PANE = 'What to do with this comment';
	const EDIT = 'Edit';
	const DELETE = 'Delete';
	const KEEP_IT = 'Keep it';
	// What is asked before a comment with nothing under it is deleted
	const DELETE_QUESTION = 'Delete this comment?';
	// What everything said under the comment is called, counted, where deleting it takes them too
	const REPLIES: CountedWords = { one: 'reply', many: 'replies' };

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	let open = $state(false);
	// Whether Delete was chosen, so the pane asks before anything is lost, in the menu's place
	let askingToDelete = $state(false);

	const deleteQuestion = $derived(deleteQuestionFor(thread.turns.length));

	/** The question before a comment is deleted, naming everything that goes with it: its replies, counted. */
	function deleteQuestionFor(replies: number): string {
		if (replies === 0) return DELETE_QUESTION;
		return `Delete this comment and its ${counted(replies, REPLIES)}?`;
	}

	/** Open or put away the menu; opened, it offers its acts again, never the question it was left on. */
	function setOpen(next: boolean) {
		open = next;
		askingToDelete = false;
	}

	/** Rewrite the comment where it stands: its words become the field. */
	function edit() {
		setOpen(false);
		review.threads.writing.openEdit(thread);
	}

	/**
	 * Delete the thread; the keyboard goes back to the line it hung under, or
	 * to what offered the block it hung on, or, for a block the story no
	 * longer draws, to the head of the story the thread stood at.
	 */
	function remove() {
		setOpen(false);
		const place = threadPlaceOf(thread.anchor);
		review.threads.remove(thread.id);
		switch (place.on) {
			case 'lines': {
				const { lines } = place;
				review.sections.keyboardToLine(lines.file, placeKey({ side: lines.side, number: lines.end_line }));
				break;
			}
			case 'story':
				// Each gives the keyboard only where it is still on nothing, in the order asked: the block first
				review.sections.keyboardToBlock(blockKey(place.block));
				review.parts.keyboardToHeadOf(OVERVIEW_PART);
				break;
		}
	}
</script>

<!-- What the reader may do to their own comment, behind three dots on the thread's bar: rewrite it, or delete it,
	which asks first in the same pane, on one line, counting what goes with it -->
<Popover
	bind:open={() => open, setOpen}
	label={askingToDelete ? deleteQuestion : MENU_PANE}
	placement="below-end"
	width="fitted"
	testId="thread-menu-pane"
>
	{#snippet trigger(control)}
		<IconButton {...control} tone="quiet" size="xs" shape="square" label={MENU} testId="thread-menu">
			<Icon name="more" size="xs" />
		</IconButton>
	{/snippet}
	{#if askingToDelete}
		<Confirmation
			question={deleteQuestion}
			goAhead={DELETE}
			keep={KEEP_IT}
			onKeep={() => setOpen(false)}
			onGoAhead={remove}
			testId="delete-dialog"
		/>
	{:else}
		<Menu testId="thread-menu-acts">
			<MenuItem tone="plain" testId="edit-comment" onclick={edit}>
				<Icon name="pencil" size="xs" />
				{EDIT}
			</MenuItem>
			<MenuItem tone="danger" testId="delete-comment" onclick={() => (askingToDelete = true)}>
				<Icon name="trash" size="xs" tone="danger" />
				{DELETE}
			</MenuItem>
		</Menu>
	{/if}
</Popover>
