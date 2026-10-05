<script lang="ts">
	import { onMount } from 'svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { panelStore } from '$lib/stores/panel.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { guideStore } from '$lib/stores/guide.svelte';
	import { currentSectionPath, isTypingTarget, moveByLine } from '$lib/utils/keyboard';
	import { scrollToComment, scrollToFile } from '$lib/utils/scroll';

	let atFile = $state(-1);

	const shortcuts: { keys: string; does: string }[] = [
		{ keys: 'j / k', does: 'Down / up a line' },
		{ keys: 'Enter', does: 'Comment on this line' },
		{ keys: '] / [', does: 'Next / previous file' },
		{ keys: 'n / p', does: 'Next / previous comment' },
		{ keys: 'a', does: 'Next unread reply' },
		{ keys: 'c', does: 'Talk to the agent' },
		{ keys: 'f', does: 'Show or hide the file tree' },
		{ keys: 'v', does: 'Mark this file viewed' },
		{ keys: 'u', does: 'Fold or unfold this file' },
		{ keys: 'Ctrl+Shift+Enter', does: 'Finish the review' },
		{ keys: '?', does: 'Show this list' },
		{ keys: 'Esc', does: 'Close it' }
	];

	/** Leave the list for the tour, which needs the review uncovered. */
	function takeTour() {
		guideStore.setHelpOpen(false);
		guideStore.startTour();
	}

	function readNews() {
		guideStore.setHelpOpen(false);
		guideStore.showNews();
	}

	function stepFile(direction: 1 | -1) {
		const files = diffStore.files;
		if (files.length === 0) return;

		const here = currentSectionPath() ?? diffStore.selectedPath;
		const from = here ? files.findIndex((f) => f.path === here) : -1;
		atFile = from === -1 ? (direction === 1 ? 0 : files.length - 1) : from + direction;
		atFile = Math.min(files.length - 1, Math.max(0, atFile));
		scrollToFile(files[atFile].path);
	}

	function stepComment(direction: 1 | -1) {
		const comment = commentStore.step(direction);
		if (!comment) return;
		if (diffStore.isCollapsed(comment.file)) diffStore.toggleCollapsed(comment.file);
		requestAnimationFrame(() => scrollToComment(comment.id, comment.file));
	}

	/** Go to the oldest thread carrying an answer nobody has looked at. */
	function stepUnread() {
		const comment = commentStore.unread[0];
		if (!comment) return;
		if (diffStore.isCollapsed(comment.file)) diffStore.toggleCollapsed(comment.file);
		requestAnimationFrame(() => {
			scrollToComment(comment.id, comment.file);
			commentStore.markRead(comment.id);
		});
	}

	/**
	 * Open the panel and put the cursor in it.
	 *
	 * Everything else in this review can be done from the keyboard; talking
	 * to the agent should not be the one thing that needs a mouse.
	 */
	function talkToAgent() {
		panelStore.setOpen(true);
		requestAnimationFrame(() =>
			document.querySelector<HTMLTextAreaElement>('[data-testid="panel-input"]')?.focus()
		);
	}

	function actOnCurrentFile(act: (path: string) => void) {
		const path = currentSectionPath() ?? diffStore.selectedPath;
		if (path) act(path);
	}

	function handle(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey || event.altKey) return;
		if (isTypingTarget(event.target)) return;

		if (guideStore.helpOpen && event.key === 'Escape') {
			guideStore.setHelpOpen(false);
			return;
		}

		const handled: Record<string, () => void> = {
			j: () => moveByLine(1),
			k: () => moveByLine(-1),
			']': () => stepFile(1),
			'[': () => stepFile(-1),
			a: stepUnread,
			n: () => stepComment(1),
			p: () => stepComment(-1),
			c: talkToAgent,
			f: () => diffStore.toggleSidebar(),
			v: () => actOnCurrentFile((path) => diffStore.toggleViewed(path)),
			u: () => actOnCurrentFile((path) => diffStore.toggleCollapsed(path)),
			'?': () => guideStore.setHelpOpen(!guideStore.helpOpen)
		};

		const act = handled[event.key];
		if (!act) return;
		event.preventDefault();
		act();
	}

	onMount(() => {
		window.addEventListener('keydown', handle);
		return () => window.removeEventListener('keydown', handle);
	});
</script>

{#if guideStore.helpOpen}
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		role="dialog"
		aria-modal="true"
		aria-label="Getting around, and the keyboard"
		tabindex="-1"
		class="fixed inset-0 z-[70] flex items-center justify-center bg-black/50"
		onclick={(e) => e.target === e.currentTarget && guideStore.setHelpOpen(false)}
		onkeydown={(e) => e.key === 'Escape' && guideStore.setHelpOpen(false)}
	>
		<div class="cr-dialog w-full max-w-md rounded-lg bg-base-100 p-6">
			<!-- The way back to the tour and the news, once their card is put away -->
			<div class="mb-5 flex flex-col gap-1">
				<button data-testid="take-tour" class="cr-guide-entry cr-guide-entry-lead" onclick={takeTour}>
					<svg class="cr-guide-compass" viewBox="0 0 20 20" aria-hidden="true">
						<circle cx="10" cy="10" r="7.5"></circle>
						<path d="M12.8 7.2l-1.7 3.9-3.9 1.7 1.7-3.9z"></path>
					</svg>
					<span class="flex-1 text-left">Take the tour again</span>
					<span class="cr-faint text-xs">{guideStore.stepCount} stops</span>
				</button>
				{#if guideStore.latestNews}
					<button data-testid="read-news" class="cr-guide-entry" onclick={readNews}>
						<svg class="cr-guide-plus" viewBox="0 0 20 20" aria-hidden="true">
							<path d="M10 3v14M3 10h14"></path>
						</svg>
						<span class="flex-1 text-left">What's new in {guideStore.latestNews.release}</span>
					</button>
				{/if}
			</div>
			<h3 class="mb-4 text-lg font-semibold">Keyboard</h3>
			<dl data-testid="shortcuts-list" class="space-y-2">
				{#each shortcuts as shortcut (shortcut.keys)}
					<div class="flex items-baseline gap-4">
						<dt class="w-40 shrink-0 font-mono text-xs" style="color: var(--cr-mark)">
							{shortcut.keys}
						</dt>
						<dd class="text-sm">{shortcut.does}</dd>
					</div>
				{/each}
			</dl>
		</div>
	</div>
{/if}
