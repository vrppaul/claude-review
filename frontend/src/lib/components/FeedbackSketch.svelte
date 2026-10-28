<!-- No props: a script, typed, only so the page's type check knows the component as every other -->
<script lang="ts"></script>

<!-- Send feedback, sketched in the review's own colours, so it follows the theme. No words: what it stands beside
	says them. Each part is painted by what it is (--cr-sketch-…). Two drawings: Help's ways keep their width, and the
	card stretches with the box, its lines as long as a share of it -->
<div data-testid="feedback-sketch" class="cr-sketch" aria-hidden="true">
	<!-- Help's three ways, one under another: the tour, the news, and Send feedback, lit -->
	<svg class="shrink-0 overflow-visible" width="70" height="84">
		<rect class="fill-(--cr-sketch-ground) stroke-(--cr-sketch-frame)" x="0.5" y="0.5" width="62" height="10" rx="2" />
		<rect class="fill-(--cr-sketch-words)" x="6" y="4.5" width="30" height="2" rx="1" />
		<rect class="fill-(--cr-sketch-ground) stroke-(--cr-sketch-frame)" x="0.5" y="14.5" width="62" height="10" rx="2" />
		<rect class="fill-(--cr-sketch-words)" x="6" y="18.5" width="26" height="2" rx="1" />
		<rect
			class="fill-(--cr-sketch-current-ring) stroke-(--cr-sketch-current-edge)"
			x="0.5"
			y="28.5"
			width="62"
			height="10"
			rx="2"
		/>
		<rect class="fill-(--cr-sketch-strong)" x="6" y="32.5" width="34" height="2" rx="1" />
	</svg>
	<!-- The card it opens: the switch of what it is, the field with what was written, the part pointed at on the
		reader's chip, the promise of what goes under its mark, and the two ways it goes, the main one last -->
	<svg class="min-w-0 flex-1 overflow-visible" height="84">
		<rect class="fill-(--cr-sketch-frame)" x="0" y="0" width="34" height="9" rx="2" />
		<rect class="fill-(--cr-sketch-strong)" x="1.5" y="1.5" width="16" height="6" rx="1.5" />
		<rect
			class="fill-(--cr-sketch-ground) stroke-(--cr-sketch-frame)"
			x="0.5"
			y="13.5"
			width="99%"
			height="20"
			rx="2.5"
		/>
		<rect class="fill-(--cr-sketch-words)" x="5" y="19" width="70%" height="2" rx="1" />
		<rect class="fill-(--cr-sketch-words)" x="5" y="25" width="46%" height="2" rx="1" />
		<rect class="fill-(--cr-sketch-current-ring)" x="0" y="38" width="42" height="6" rx="2" />
		<rect class="fill-(--cr-sketch-promise)" x="0" y="49" width="99%" height="14" rx="2.5" />
		<rect class="fill-(--cr-sketch-strong)" x="5" y="54.5" width="4" height="4" rx="1" />
		<rect class="fill-(--cr-sketch-strong)" x="13" y="55.5" width="58%" height="2" rx="1" />
		<rect
			class="fill-(--cr-sketch-ground) stroke-(--cr-sketch-act-edge)"
			x="52%"
			y="71.5"
			width="22%"
			height="10"
			rx="2"
		/>
		<rect class="fill-(--cr-sketch-main-act)" x="77%" y="71" width="22%" height="11" rx="2" />
	</svg>
</div>
