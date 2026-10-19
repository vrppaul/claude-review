<script lang="ts">
	// A drawing for the 1.5.0 release news.
	import Icon from '$lib/ui/Icon.svelte';
</script>

<!-- A comment being written with a screenshot pasted under it, drawn in the
	review's own colours so it follows the theme -->
<div class="cr-illustration" aria-hidden="true">
	<div class="cr-illustration-thumb">
		<span class="cr-illustration-line cr-illustration-line-added"></span>
		<span class="cr-illustration-line"></span>
		<span class="cr-illustration-line cr-illustration-line-short"></span>
		<span class="cr-illustration-detach"><Icon name="cross" size="xs" /></span>
	</div>
	<div class="cr-illustration-field">Why does this wrap here?</div>
</div>
