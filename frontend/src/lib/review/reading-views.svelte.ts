/**
 * The ways a review is read, and which of them is on screen.
 *
 * How the reader likes to read is theirs and outlives a review: it is kept
 * with the page's layout, and a review opens the way it says. What is on
 * screen is the review's own. The reader choosing a view changes both;
 * being taken to something only one view draws changes what is on screen,
 * and leaves the choice as the reader made it.
 *
 * Read as Files, against the review's own base, every thread and file the
 * review holds is drawn: in the change's files, above them where its file
 * is gone, or in a file the change did not touch, read alone. A story draws
 * what it tells and what it leaves out, and a narrower base the lines it
 * shows. Whatever takes the reader to something the view on screen does not
 * draw asks here for the view that does, in one place.
 */

import type { ThreadLines } from '$lib/anchors/views';
import type { PageLayout, ReadingChoice } from '$lib/reader/page-layout.svelte';
import type { FileAloneReading } from '$lib/review/file-alone-reading.svelte';
import { whereRead } from '$lib/review/files-way';
import type { ViewsOnScreen } from '$lib/review/navigator';
import type { ReadingView, ReadingViewName } from '$lib/review/reading-view';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';

/** Each view a review is read in, by its name: a file read alone by what only it does. */
interface Views {
	files: ReadingView;
	story: ReadingView;
	'file-alone': FileAloneReading;
}

/** How the reader chose to read last, as the page's layout keeps it. */
type KeptChoice = PageLayout['readingView'];

// The view every review can be read in, which draws the change's files; and the one a file it did not touch is
// read alone in
const FILES: ReadingViewName = 'files';
const FILE_ALONE = 'file-alone' satisfies ReadingViewName;

export class ReadingViews implements ViewsOnScreen {
	readonly #views: Views;
	readonly #kept: KeptChoice;
	readonly #diff: ReviewDiff;
	#nameOnScreen: ReadingViewName;

	/**
	 * @param views each view this review is read in
	 * @param kept how the reader chose to read last, in whichever review
	 * @param mayOpenAsStory whether this review may open as its story: any other opens by its files,
	 *   though the reader chose the story last
	 * @param diff the review's own diff, which says where a thread is read, and which a narrower base may be in
	 *   force on
	 */
	constructor(views: Views, kept: KeptChoice, mayOpenAsStory: boolean, diff: ReviewDiff) {
		this.#views = views;
		this.#kept = kept;
		this.#diff = diff;
		this.#nameOnScreen = $state(mayOpenAsStory ? kept.name : FILES);
	}

	/** The view the review is read in now. */
	get onScreen(): ReadingView {
		return this.#views[this.#nameOnScreen];
	}

	/** The view a file the change did not touch is read alone in, on screen or not. */
	get fileAlone(): FileAloneReading {
		return this.#views[FILE_ALONE];
	}

	/** The file read alone now; null while another view is on screen. */
	get fileReadAlone(): string | null {
		return this.#nameOnScreen === FILE_ALONE ? this.fileAlone.path : null;
	}

	/** Read the review the way the reader chooses, and the next review they open too. */
	choose(name: ReadingChoice): void {
		this.#nameOnScreen = name;
		this.#kept.set(name);
	}

	/**
	 * Bring a view on screen for something it draws — what only it shows, a
	 * place the reader read in it — and hand it over: how the reader chose to
	 * read stays as they chose it.
	 */
	show(name: ReadingViewName): ReadingView {
		this.#nameOnScreen = name;
		return this.#views[name];
	}

	/**
	 * Bring on screen the change's files read against the review's own base,
	 * and hand their view over, as it is if the whole review could not be put
	 * back: the diff keeps why, and the files' bar says it.
	 */
	async showTheChange(): Promise<ReadingView> {
		const files = this.show(FILES);
		if (this.#diff.narrowed) await this.#diff.showWholeReview();
		return files;
	}

	/** Bring a file the change did not touch on screen alone, and hand its view over once the file is read. */
	async readAlone(path: string): Promise<ReadingView> {
		const alone = this.fileAlone;
		const reading = alone.open(path);
		this.#nameOnScreen = FILE_ALONE;
		await reading;
		return alone;
	}

	/** Bring on screen the view of the Files way of reading that draws a thread on these lines, and hand it over. */
	showWhereRead(lines: ThreadLines): Promise<ReadingView> {
		return whereRead(lines, this.#diff) === 'in-its-file-alone' ? this.readAlone(lines.file) : this.showTheChange();
	}
}
