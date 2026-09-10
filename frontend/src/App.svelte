<script lang="ts">
	import { onMount } from 'svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { openSession, tellServer } from '$lib/stores/session.svelte';
	import { reviewStore } from '$lib/stores/review.svelte';
	import { panelStore } from '$lib/stores/panel.svelte';
	import { soundStore } from '$lib/stores/sound.svelte';
	import { markTab } from '$lib/utils/tab';
	import { quoteFrom } from '$lib/utils/reanchor';
	import { showFile } from '$lib/utils/scroll';
	import AgentPanel from '$lib/components/AgentPanel.svelte';
	import FileList from '$lib/components/FileList.svelte';
	import DiffNotice from '$lib/components/DiffNotice.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import SubmitBar from '$lib/components/SubmitBar.svelte';
	import KeyboardShortcuts from '$lib/components/KeyboardShortcuts.svelte';

	let loading = $state(true);
	let error = $state<string | null>(null);
	let restored = $state(0);

	onMount(() => {
		diffStore
			.fetchDiff()
			.then(() => {
				// An unsent review of the same thing is picked up where it stopped,
				// the conversation in the panel with it
				restored = commentStore.restore(diffStore.title);
				panelStore.restore(diffStore.title);
				panelStore.report(diffStore.agent);
				if (reviewStore.canSendRound) panelStore.offer();
				// The draft may know a later round than a restarted server does
				tellServer();
			})
			.catch((e) => {
				error = e instanceof Error ? e.message : 'Failed to load diff';
			})
			.finally(() => {
				loading = false;
			});

		// Holding this open is what tells the server the review is still on
		// screen; a poll is throttled to a crawl in a background tab.
		return openSession(handle, () => ({
			round: reviewStore.round,
			threads: commentStore.onTheWire
		}));
	});

	/** What the server has to say while the review is open. */
	function handle(message: { type: string; [key: string]: unknown }) {
		if (message.type === 'reply' && typeof message.text === 'string') {
			commentStore.receiveReply(
				String(message.thread_id),
				message.text,
				typeof message.question_id === 'string' ? message.question_id : undefined
			);
			soundStore.announce();
		} else if (message.type === 'answerer') {
			reviewStore.attachAnswerer();
			panelStore.offer();
		} else if (message.type === 'chat' && typeof message.text === 'string') {
			panelStore.receive(
				typeof message.message_id === 'string' ? message.message_id : undefined,
				message.text,
				Array.isArray(message.files) ? message.files.map(String) : []
			);
			soundStore.announce();
		} else if (message.type === 'progress' && typeof message.text === 'string') {
			panelStore.reportProgress(
				typeof message.message_id === 'string' ? message.message_id : undefined,
				message.text,
				Array.isArray(message.files) ? message.files.map(String) : [],
				Array.isArray(message.steps)
					? message.steps.map((step) => ({
							text: String((step as { text: unknown }).text),
							done: (step as { done: unknown }).done === true
						}))
					: []
			);
		} else if (message.type === 'show' && typeof message.file === 'string') {
			// Asked for: the agent does not move this screen on its own
			showFile(message.file);
		} else if (message.type === 'status') {
			panelStore.report({
				model: typeof message.model === 'string' ? message.model : null,
				context: typeof message.context === 'string' ? message.context : null,
				at: typeof message.at === 'number' ? message.at : null
			});
		} else if (message.type === 'point' && typeof message.body === 'string') {
			raise(message);
		} else if (message.type === 'changed' && typeof message.files === 'number') {
			// Said, never acted on: swapping the diff under a half-written
			// comment would orphan it
			diffStore.noteTreeMoved(message.files);
		} else if (message.type === 'round' && typeof message.number === 'number') {
			reviewStore.setRound(message.number);
		} else if (message.type === 'diff') {
			landed(
				Array.isArray(message.changed) ? message.changed.map(String) : null,
				typeof message.since === 'number' ? message.since : null
			).catch((e) => {
				// A round landing half-applied is worse than not at all: the code
				// under the reader has moved and their threads have not
				panelStore.note(
					`the diff could not be taken again — ${e instanceof Error ? e.message : 'reload the review'}`
				);
			});
		}
	}

	/**
	 * Take in the work a round asked for, now it has landed.
	 *
	 * The threads move onto the review's own diff — one whose lines survived
	 * follows them, one whose lines are gone says so — and that diff is the
	 * one they are anchored in, whatever narrower base is being read on
	 * screen. Which files changed is what takes the tick off the ones the
	 * agent rewrote.
	 */
	async function landed(changed: string[] | null, since: number | null) {
		const anchors = await diffStore.takeAgain();
		const moved = commentStore.reanchorAll(anchors);
		diffStore.noteRetaken(moved, changed, since);
		// The conversation is about code that has just changed under it, so
		// the panel says where one lot of answers stops applying
		panelStore.note(retaken(moved));
	}

	/**
	 * Put a thread the author raised onto the diff, and say so in the panel.
	 *
	 * It arrives as numbers, so the lines themselves are read off the diff on
	 * screen: without them the thread cannot follow its code when it moves.
	 */
	function raise(message: { type: string; [key: string]: unknown }) {
		const file = String(message.file);
		const side = message.side === 'old' ? 'old' : 'new';
		const start = Number(message.start_line);
		const end = Number(message.end_line);
		const severity =
			message.severity === 'question' || message.severity === 'blocker'
				? message.severity
				: 'note';

		const id = commentStore.raise(
			String(message.thread_id),
			file,
			side,
			start,
			end,
			String(message.body),
			severity,
			quoteFrom(diffStore.files.find((f) => f.path === file)?.hunks ?? null, side, start, end)
		);
		panelStore.note(`pointed at ${file.split('/').pop()} ${start}${end !== start ? `-${end}` : ''}`, [
			id
		]);
		soundStore.announce();
	}

	/** What a retaken diff did to the threads hanging on it. */
	function retaken({ followed, outdated }: { followed: number; outdated: number }): string {
		const parts = [`diff retaken · ${diffStore.files.length} files`];
		if (followed > 0) parts.push(`${followed} threads followed their lines`);
		if (outdated > 0) parts.push(`${outdated} outdated`);
		return parts.join(' · ');
	}

	// An answer can arrive while the review is in a background tab, where
	// neither the dot beside the thread nor the panel can be seen
	$effect(() => {
		markTab(commentStore.unreadCount + panelStore.unread, diffStore.title || 'Claude Review');
	});
</script>

{#if loading}
	<div class="flex items-center justify-center min-h-screen">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if error}
	<div class="flex items-center justify-center min-h-screen">
		<div class="alert alert-error max-w-md">
			<span>{error}</span>
		</div>
	</div>
{:else if diffStore.files.length === 0 && !diffStore.narrowed}
	<div class="flex items-center justify-center min-h-screen">
		<div class="alert alert-info max-w-md">
			<span>No changes found.</span>
		</div>
	</div>
{:else}
	<KeyboardShortcuts />
	<div class="flex h-screen flex-col">
	{#if restored > 0}
		<div
			data-testid="restored-notice"
			class="flex items-center gap-3 border-b border-base-300 bg-base-200 px-4 py-1.5 text-xs"
		>
			<span>
				Picked up {restored}
				{restored === 1 ? 'comment' : 'comments'} you had not sent yet.
			</span>
			<button class="btn btn-ghost btn-xs" onclick={() => (restored = 0)}>Dismiss</button>
		</div>
	{/if}
		<SubmitBar />
		<DiffNotice />
		<div class="flex min-h-0 flex-1">
			{#if diffStore.sidebarOpen}
				<FileList />
			{:else}
				<!-- Where the tree was, so the way back is where it went -->
				<button
					data-testid="show-sidebar"
					class="cr-tree-rail"
					title="Bring the file tree back"
					aria-label="Bring the file tree back"
					onclick={() => diffStore.toggleSidebar()}
				>
					<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
						<path d="M4.5 2L8 6l-3.5 4z" />
					</svg>
				</button>
			{/if}
			<DiffView />
			{#if panelStore.open}
				<AgentPanel />
			{/if}
		</div>
	</div>
{/if}
