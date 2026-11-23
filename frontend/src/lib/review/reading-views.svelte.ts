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
 *
 * A reader the page brings the story on screen for is trying Story: a
 * thread only the story draws brought it, or the review opened the way they
 * read last. Every way the page brings it passes through here, so nothing
 * watches what is on screen to catch it after.
 *
 * A view's place is lost with it as it leaves the screen, and only here is
 * it known to be leaving while it is still drawn. So where the reader leaves
 * each way of reading is kept here, and choosing that way again brings them
 * back there. Only their choice does: a view brought for something goes
 * where that takes it.
 */

import type { ThreadLines } from '$lib/anchors/views';
import type { PageLayout, ReadingChoice } from '$lib/reader/page-layout.svelte';
import type { FileAloneReading } from '$lib/review/file-alone-reading.svelte';
import { whereRead } from '$lib/review/files-way';
import type { ViewsOnScreen } from '$lib/review/navigator';
import {
	type FilesReading,
	type PlaceLeft,
	placeLeftIn,
	type ReadingView,
	type ReadingViewName
} from '$lib/review/reading-view';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';
import type { StoryReading } from '$lib/review/story-reading';

/** Each view a review is read in, by its name, and by what only it does. */
interface Views {
	files: FilesReading;
	story: StoryReading;
	'file-alone': FileAloneReading;
}

/** How the reader chose to read last, as the page's layout keeps it. */
type KeptChoice = PageLayout['readingView'];

/** Whoever keeps that Story was introduced to the reader. */
export interface StoryIntroductions {
	noteStoryIntroduced: () => void;
}

// The view every review can be read in, which draws the change's files; the one a file it did not touch is read
// alone in; and the story's, which the reader is trying while it is on screen
const FILES: ReadingViewName = 'files';
const FILE_ALONE = 'file-alone' satisfies ReadingViewName;
const STORY: ReadingViewName = 'story';

export class ReadingViews implements ViewsOnScreen {
	readonly #views: Views;
	readonly #kept: KeptChoice;
	readonly #diff: ReviewDiff;
	readonly #introductions: StoryIntroductions;
	#nameOnScreen: ReadingViewName;
	// Where the reader last left each way of reading; none where they read nothing in it
	readonly #placesKept: Record<ReadingChoice, PlaceLeft | null> = { files: null, story: null };

	/**
	 * @param views each view this review is read in
	 * @param kept how the reader chose to read last, in whichever review
	 * @param mayOpenAsStory whether this review may open as its story: any other opens by its files,
	 *   though the reader chose the story last
	 * @param diff the review's own diff, which says where a thread is read, and which a narrower base may be in
	 *   force on
	 * @param introductions whoever keeps that Story was introduced, which the story on screen is
	 */
	constructor(
		views: Views,
		kept: KeptChoice,
		mayOpenAsStory: boolean,
		diff: ReviewDiff,
		introductions: StoryIntroductions
	) {
		this.#views = views;
		this.#kept = kept;
		this.#diff = diff;
		this.#introductions = introductions;
		this.#nameOnScreen = $state(FILES);
		this.#bring(mayOpenAsStory ? kept.name : FILES);
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

	/**
	 * Read the review the way the reader chooses, and the next review they
	 * open too. A way they come back to is where they left it, the keyboard
	 * left on whatever they chose it with; one they read nothing in, or a
	 * file no longer in the change, from its top.
	 */
	choose(name: ReadingChoice): void {
		// The reader asked: whatever they asked through (`WayIntoStory`) notes the story tried
		this.#kept.set(name);
		// The view chosen is the one read: whatever was left in it before, the reader is in it now
		if (name === this.#nameOnScreen) return;
		// Read before the view on screen leaves, which keeps its own place under its way of reading
		const left = this.#placesKept[name];
		const view = left === null ? name : this.#viewDrawingNow(left);
		if (view === this.#nameOnScreen) return;
		this.#putOnScreen(view);
		if (left !== null) void this.#views[view].returnTo(left.place, 'where-it-is');
	}

	/**
	 * Bring a view on screen for something it draws — what only it shows, a
	 * place the reader read in it — and hand it over: how the reader chose to
	 * read stays as they chose it.
	 */
	show(name: ReadingViewName): ReadingView {
		this.#bring(name);
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
		this.#bring(FILE_ALONE);
		await reading;
		return alone;
	}

	/**
	 * Bring the change's files on screen in place of a file read alone that
	 * the change now holds, taken again, and have them take the reader over
	 * on the line they read (`FilesReading.takeOver`). A file the change
	 * still leaves stays read alone as it is.
	 */
	async giveWayToTheChange(): Promise<void> {
		const path = this.fileAlone.path;
		if (path === null || !this.#readAmongTheFilesNow(this.#nameOnScreen, path)) return;
		const read = this.onScreen.placeRead();
		const files = this.#views.files;
		this.#bring(FILES);
		if (read !== null) await files.takeOver(read.place);
	}

	/** Bring on screen the view of the Files way of reading that draws a thread on these lines, and hand it over. */
	showWhereRead(lines: ThreadLines): Promise<ReadingView> {
		return whereRead(lines, this.#diff) === 'in-its-file-alone' ? this.readAlone(lines.file) : this.showTheChange();
	}

	/**
	 * Bring on screen the view of the Files way of reading that draws a file, and hand it over: the change's files
	 * where the change holds it, or else the file read alone.
	 */
	showWhereFileRead(path: string): Promise<ReadingView> {
		return this.#diff.holds(path) ? this.showTheChange() : this.readAlone(path);
	}

	/** Bring a view on screen for the reader: the story brought is being tried. */
	#bring(name: ReadingViewName): void {
		this.#putOnScreen(name);
		if (name === STORY) this.#introductions.noteStoryIntroduced();
	}

	/** Put a view on screen, keeping where the reader leaves the one there under the way of reading it is one of. */
	#putOnScreen(name: ReadingViewName): void {
		if (name === this.#nameOnScreen) return;
		const leaving = this.onScreen;
		this.#placesKept[leaving.readAs] = placeLeftIn(leaving);
		this.#nameOnScreen = name;
	}

	/** The view that draws a place left now: the one it was read in, or the change's files (`#readAmongTheFilesNow`). */
	#viewDrawingNow(left: PlaceLeft): ReadingViewName {
		return this.#readAmongTheFilesNow(left.view, left.place.within) ? FILES : left.view;
	}

	/** Whether a section of a view is a file read alone that the change has come to hold, read among its files now. */
	#readAmongTheFilesNow(view: ReadingViewName, section: string): boolean {
		// What a view of files whole knows a section by is its file's path
		return view === FILE_ALONE && this.#diff.holds(section);
	}
}
