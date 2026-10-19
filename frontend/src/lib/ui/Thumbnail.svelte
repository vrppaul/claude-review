<script lang="ts">
	import BreathingDots from './BreathingDots.svelte';
	import Icon from './Icon.svelte';
	import IconButton from './IconButton.svelte';

	/**
	 * What it shows:
	 * - image: the image, shrunk to the square; told when it cannot be drawn
	 * - uploading: dots that breathe, while the image is on its way to the review
	 * - lost: words saying the image can no longer be shown, where it was
	 */
	type Shows =
		| { shows: 'image'; src: string; alt: string; onLost: () => void }
		| { shows: 'uploading' }
		| { shows: 'lost'; said: string };

	/**
	 * What can be done with it: nothing; open the image at its full size in a tab of its own; or take it off what
	 * is being written, by a cross over its corner.
	 */
	type Reach =
		| { opens?: never; removing?: never }
		| { opens: Opening; removing?: never }
		| { opens?: never; removing: Removing };

	interface Opening {
		/** Where the image is at its full size. */
		href: string;
		/** The link's test id. */
		testId: string;
	}

	interface Removing {
		/** What the cross does, said to whoever cannot see it and under the pointer. */
		label: string;
		/** Whether it is shut, while what it is on is being sent. */
		disabled: boolean;
		onRemove: () => void;
		/** The cross's test id. */
		testId: string;
	}

	type Props = Shows & Reach & { testId: string };

	let props: Props = $props();
</script>

<!-- An image pasted into what is said, shrunk to a square of one size at a field's corner -->
{#snippet square()}
	{#if props.shows === 'image'}
		<img
			data-testid={props.testId}
			src={props.src}
			alt={props.alt}
			class="cr-ui-thumbnail"
			loading="lazy"
			onerror={props.onLost}
		/>
	{:else if props.shows === 'uploading'}
		<span data-testid={props.testId} class="cr-ui-thumbnail cr-ui-thumbnail-filled">
			<BreathingDots tone="quiet" testId="{props.testId}-dots" />
		</span>
	{:else}
		<span data-testid={props.testId} class="cr-ui-thumbnail cr-ui-thumbnail-filled cr-ui-thumbnail-lost">
			{props.said}
		</span>
	{/if}
{/snippet}

{#if props.opens}
	<!-- Opened at its full size in a tab of its own: what it stands in is too narrow to read a screenshot in -->
	<a data-testid={props.opens.testId} href={props.opens.href} target="_blank" rel="noopener noreferrer">
		{@render square()}
	</a>
{:else if props.removing}
	<span class="cr-ui-thumbnail-removable">
		{@render square()}
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
{:else}
	{@render square()}
{/if}
