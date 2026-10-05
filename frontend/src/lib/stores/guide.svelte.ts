/**
 * Showing a reader around: the welcome, what is new, and the tour.
 *
 * One card, bottom left. Somebody who has never opened a review is
 * welcomed; somebody whose last review was an older release is told what
 * changed, when there is anything to tell; everybody else sees nothing.
 * The tour narrates from that same card while a light moves over the review.
 */

import type { CommentRoute, TourStep } from "$lib/guide/tour";
import type { CommentFieldEvent } from "$lib/types";
import { stepsFor } from "$lib/guide/tour";
import { RELEASE_NEWS, type ReleaseNews } from "$lib/guide/news";
import { latestNews, unseenNews } from "$lib/guide/news-choice";
import { reviewStore } from "$lib/stores/review.svelte";
import {
  isNewer,
  readSeenRelease,
  writeSeenRelease,
} from "$lib/utils/seen-release";

export type GuideCard = "welcome" | "news";

let card = $state<GuideCard | null>(null);
// The ? list: the tour, the news and the keys. Opened by the key or by the
// button in the header — a browser extension may have the key for itself.
let helpOpen = $state(false);
let news = $state<ReleaseNews | undefined>(undefined);
let touring = $state(false);
let stepIndex = $state(0);
let route = $state<CommentRoute>("review");
let release = $state<string | null>(null);
// Comment fields on a line open right now, so a step asking for one that is
// already open does not wait for something that has happened
let openNewComments = 0;
// Whether a step has anything on the page to light. The page answers; until
// it is attached every step counts as shown.
let isOnPage: (targets: string[]) => boolean = () => true;

const steps = $derived(stepsFor({ attached: reviewStore.canSendRound, route }));

/** Remember this release as seen, so the card does not come back. */
function settle(): void {
  if (release) writeSeenRelease(release);
}

function shows(step: TourStep): boolean {
  if (!isOnPage(step.targets)) return false;
  return !(step.waitsFor?.kind === "comment-opened" && openNewComments > 0);
}

/**
 * Land on the first step from here, going this way, that has something to show.
 *
 * Going back past the start turns round, so the first step shown is always
 * one there is something to see in; going on past the end ends the tour.
 */
function landFrom(index: number, direction: 1 | -1): void {
  let candidate = index;
  while (
    candidate >= 0 &&
    candidate < steps.length &&
    !shows(steps[candidate])
  ) {
    candidate += direction;
  }
  if (candidate < 0) {
    landFrom(0, 1);
    return;
  }
  if (candidate >= steps.length) {
    touring = false;
    return;
  }
  stepIndex = candidate;
}

/** The steps this tour shows, in order: those with something on the page. */
function shownSteps(): TourStep[] {
  return steps.filter(shows);
}

/** The count of comment fields on a line, after one of them said something. */
function countOpen(event: CommentFieldEvent): void {
  if (event.kind !== "new") return;
  openNewComments = Math.max(
    0,
    openNewComments + (event.type === "opened" ? 1 : -1),
  );
}

export const guideStore = {
  get card(): GuideCard | null {
    return card;
  },
  get helpOpen(): boolean {
    return helpOpen;
  },

  setHelpOpen(open: boolean) {
    helpOpen = open;
  },
  get news(): ReleaseNews | undefined {
    return news;
  },
  get touring(): boolean {
    return touring;
  },
  get step(): TourStep | undefined {
    return touring ? steps[stepIndex] : undefined;
  },
  /**
   * Where this step stands among the steps the reader will actually see —
   * a plan has no base to choose, so its tour is shorter, and says so.
   */
  get stepPosition(): number {
    const current = steps[stepIndex];
    return current ? shownSteps().indexOf(current) : -1;
  },
  get stepCount(): number {
    return shownSteps().length;
  },
  get isLastStep(): boolean {
    return !steps.slice(stepIndex + 1).some(shows);
  },
  /** Whether there is a step before this one to go back to. */
  get canGoBack(): boolean {
    return steps.slice(0, stepIndex).some(shows);
  },
  /** The newest news up to this release, to read again from the ? list. */
  get latestNews(): ReleaseNews | undefined {
    return release ? latestNews(RELEASE_NEWS, release) : undefined;
  },

  /** Let the page say which steps have something to show. */
  readPageWith(predicate: (targets: string[]) => boolean) {
    isOnPage = predicate;
  },

  /** Decide what to show a reader arriving at a review served by this release. */
  open(serving: string) {
    release = serving;
    const seen = readSeenRelease();
    if (seen === null) {
      card = "welcome";
      return;
    }
    if (!isNewer(serving, seen)) return;
    news = unseenNews(RELEASE_NEWS, seen, serving);
    if (news) card = "news";
    // Nothing worth telling: a patch is remembered as seen without a word
    else settle();
  },

  /** Put the card away, for this release. */
  dismiss() {
    card = null;
    settle();
  },

  showNews() {
    news = this.latestNews;
    if (news) card = "news";
  },

  startTour() {
    card = null;
    settle();
    route = "review";
    touring = true;
    landFrom(0, 1);
  },

  endTour() {
    touring = false;
  },

  next() {
    landFrom(stepIndex + 1, 1);
  },

  back() {
    landFrom(stepIndex - 1, -1);
  },

  /**
   * Hear what happened to a comment field, and move on if it was awaited.
   *
   * Called once the page shows the result, so the step it leads to finds
   * what it lights.
   */
  notice(event: CommentFieldEvent) {
    countOpen(event);
    const waiting = this.step?.waitsFor;
    if (!waiting || event.kind !== "new") return;

    if (waiting.kind === "comment-opened") {
      if (event.type === "opened") this.next();
      return;
    }
    if (event.type === "added" && waiting.routes.includes("review")) {
      this.choose("review");
    } else if (event.type === "asked" && waiting.routes.includes("ask")) {
      this.choose("ask");
    } else if (event.type === "closed" && openNewComments === 0) {
      // While another comment on a line is open, that one is still to be sent
      this.back();
    }
  },

  /** The reader chose where a comment goes; the next step shows what came of it. */
  choose(chosen: CommentRoute) {
    route = chosen;
    this.next();
  },

  /** Restart from nothing, as a new page would. */
  clear() {
    card = null;
    helpOpen = false;
    news = undefined;
    touring = false;
    stepIndex = 0;
    route = "review";
    release = null;
    openNewComments = 0;
    isOnPage = () => true;
  },
};
