<script lang="ts">
	interface Props {
		src: string;
		/** What the picture shows, for whoever cannot see it. */
		alt: string;
		testId: string;
	}

	let { src, alt, testId }: Props = $props();
</script>

<!-- A picture of something, a release's news say: as wide as what it stands in, at a box's corner, edged as a
	surface is. A thumbnail of an image pasted into what is said is a Thumbnail -->
<img data-testid={testId} class="cr-ui-picture" {src} {alt} />
