<script lang="ts">
	import BreathingDots from './BreathingDots.svelte';
	import Icon from './Icon.svelte';
	import IconButton from './IconButton.svelte';

	/**
	 * What can be done with an image shown: open it at its full size in a tab of its own, by a link known by its
	 * test id; or take it off what is being written, by a cross over its corner.
	 */
	type Reach = { opensAs: string; removing?: never } | { opensAs?: never; removing: Removing };

	interface Removing {
		/** What the cross does, said to whoever cannot see it and under the pointer. */
		label: string;
		/** Whether it is shut, while what it is on is being sent. */
		disabled: boolean;
		onRemove: () => void;
		/** The cross's test id. */
		testId: string;
	}

	/**
	 * What it shows:
	 * - image: the image, shrunk to the square, told when it cannot be drawn, and what can be done with it
	 * - uploading: dots that breathe, while the image is on its way to the review
	 * - lost: words saying the image can no longer be shown, where it was
	 */
	type Shows =
		| ({ shows: 'image'; src: string; alt: string; onLost: () => void } & Reach)
		| { shows: 'uploading' }
		| { shows: 'lost'; said: string };

	type Props = Shows & { testId: string };

	let props: Props = $props();
</script>

<!-- An image pasted into what is said, shrunk to a square of one size at a field's corner -->
{#if props.shows === 'image'}
	{#snippet image(src: string, alt: string, onLost: () => void)}
		<img data-testid={props.testId} {src} {alt} class="cr-ui-thumbnail" loading="lazy" onerror={onLost} />
	{/snippet}
	{#if props.opensAs}
		<!-- Opened at its full size in a tab of its own: what it stands in is too narrow to read a screenshot in -->
		<a data-testid={props.opensAs} href={props.src} target="_blank" rel="noopener noreferrer">
			{@render image(props.src, props.alt, props.onLost)}
		</a>
	{:else if props.removing}
		<span class="cr-ui-thumbnail-removable">
			{@render image(props.src, props.alt, props.onLost)}
			<span class="cr-ui-thumbnail-remove">
				<IconButton
					tone="secondary"
					size="xs"
					label={props.removing.label}
					testId={props.removing.testId}
					disabled={props.removing.disabled}
					onclick={props.removing.onRemove}
				>
					<Icon name="cross" size="xs" />
				</IconButton>
			</span>
		</span>
	{/if}
{:else if props.shows === 'uploading'}
	<span data-testid={props.testId} class="cr-ui-thumbnail cr-ui-thumbnail-filled">
		<BreathingDots tone="quiet" testId="{props.testId}-dots" />
	</span>
{:else}
	<span data-testid={props.testId} class="cr-ui-thumbnail cr-ui-thumbnail-filled cr-ui-thumbnail-lost">
		{props.said}
	</span>
{/if}
