<script lang="ts">
	import { onMount } from 'svelte';
	import type { ChangesSince, FollowOutcome, PointPush, ServerPush } from '$lib/types';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { dispatchHeld, openSession, tellServer } from '$lib/stores/session.svelte';
	import { reviewStore } from '$lib/stores/review.svelte';
	import { panelStore } from '$lib/stores/panel.svelte';
	import { settingsStore } from '$lib/stores/settings.svelte';
	import { soundStore } from '$lib/stores/sound.svelte';
	import { themeStore } from '$lib/stores/theme.svelte';
	import { markTab } from '$lib/utils/tab';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { showFile } from '$lib/utils/scroll';
	import AgentPanel from '$lib/components/AgentPanel.svelte';
	import FileList from '$lib/components/FileList.svelte';
	import DiffNotice from '$lib/components/DiffNotice.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import SubmitBar from '$lib/components/SubmitBar.svelte';
	import KeyboardShortcuts from '$lib/components/KeyboardShortcuts.svelte';
	import Guide from '$lib/components/Guide.svelte';
	import { guideStore } from '$lib/stores/guide.svelte';

	let loading = $state(true);
	let error = $state<string | null>(null);
	let restored = $state(0);

	onMount(() => {
		const stopTheme = themeStore.start();
		// The reader's settings first: whether whitespace counts decides which
		// diff is asked for
		settingsStore
			.load()
			.then(() => diffStore.fetchDiff())
			.then(() => {
				// An unsent review of the same thing is picked up where it stopped,
				// the conversation in the panel with it
				restored = commentStore.restore(diffStore.title);
				panelStore.restore(diffStore.title);
				panelStore.report(diffStore.agent);
				if (reviewStore.canSendRound) panelStore.offer();
				// The draft may know a later round than a restarted server does
				tellServer();
				// Only now is there a draft for what the server said meanwhile to land in
				dispatchHeld();
				// A first review is welcomed; a newer release says what changed
				void guideStore.open(diffStore.release);
			})
			.catch((e) => {
				error = e instanceof Error ? e.message : 'Failed to load diff';
			})
			.finally(() => {
				loading = false;
			});

		// Holding this open is what tells the server the review is still on
		// screen; a poll is throttled to a crawl in a background tab.
		const closeSession = openSession(handle, () => ({
			round: reviewStore.round,
			threads: commentStore.onTheWire
		}));
		return () => {
			closeSession();
			stopTheme();
		};
	});

	/** What the server has to say while the review is open. */
	function handle(push: ServerPush) {
		switch (push.type) {
			case 'reply':
				// The wire says null where the store says nothing was named
				commentStore.receiveReply(push.thread_id, push.body, push.question_id ?? undefined);
				soundStore.announce();
				return;
			case 'answerer':
				if (!push.attached) return;
				reviewStore.attachAnswerer();
				panelStore.offer();
				return;
			case 'chat':
				panelStore.receive(push.message_id ?? undefined, push.body, push.files);
				soundStore.announce();
				return;
			case 'progress':
				panelStore.showWork(push.work);
				return;
			case 'show':
				// Asked for: the agent does not move this screen on its own
				showFile(push.file);
				return;
			case 'status':
				panelStore.report(push.agent);
				return;
			case 'point':
				raise(push);
				return;
			case 'changed':
				// Said, never acted on: swapping the diff under a half-written
				// comment would orphan it
				diffStore.noteTreeMoved(push.moved_count);
				return;
			case 'round':
				reviewStore.setRound(push.number);
				return;
			case 'diff':
				landed(push.changes).catch((e) => {
					// A round landing half-applied is worse than not at all: the code
					// under the reader has moved and their threads have not
					panelStore.note(
						`the diff could not be taken again — ${e instanceof Error ? e.message : 'reload the review'}`
					);
				});
				return;
			default:
				unknown(push);
		}
	}

	/**
	 * A push of a kind this page does not handle. The session passes over
	 * kinds it does not know, and the compiler refuses a known kind left out
	 * of the switch above, so this only says so if both are ever wrong.
	 */
	function unknown(push: never) {
		console.warn('claude-review: the server pushed something this page does not know', push);
	}

	/**
	 * Take in the work a round asked for, now it has landed.
	 *
	 * The threads move onto the review's own diff — one whose lines survived
	 * follows them, one whose lines are gone says so — whatever narrower base
	 * is being read on screen. Which files changed is what takes the tick off
	 * the ones the agent rewrote.
	 *
	 * The threads go first: the server already holds the new diff, and a
	 * thread left on old numbers would be kept that way in the draft, while a
	 * diff that failed to arrive comes back with a reload.
	 */
	async function landed(changes: ChangesSince | null) {
		const moved = await commentStore.follow();
		await diffStore.fetchDiff();
		diffStore.noteRetaken(moved, changes);
		// The conversation is about code that has just changed under it, so
		// the panel says where one lot of answers stops applying
		panelStore.note(retaken(moved));
	}

	/** Put a thread the author raised onto the diff, and say so in the panel. */
	function raise(push: PointPush) {
		// The server quoted it from the diff it checked the lines against
		const id = commentStore.raise(push.thread_id, push.anchor, push.body, push.severity);
		panelStore.note(`pointed at ${anchorShortPlace(push.anchor)}`, [id]);
		soundStore.announce();
	}

	/** What a retaken diff did to the threads hanging on it. */
	function retaken({ followed, outdated }: FollowOutcome): string {
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
	<Guide />
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
					data-testid="show-sidebar" data-tour="file-tree"
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
