/**
 * What each release changed, as a reader who last saw an older one is told.
 *
 * Written by hand, one entry per release worth telling about, newest last.
 * A release with no entry says nothing of its own, so a patch that only
 * fixes things stays quiet.
 */

/** The drawings an entry can ask for, by name; `NewsIllustration` draws them. */
export type DrawingName = "pasted-screenshot";

/**
 * A picture above the words. Either a file — a screenshot, or a GIF to show
 * something moving — imported beside the entry so the build carries it; or a
 * small drawing in markup, which follows the theme.
 */
export type Illustration =
  | { kind: "image"; src: string; alt: string }
  | { kind: "drawing"; name: DrawingName };

export interface ReleaseNews {
  release: string;
  title: string;
  body: string;
  /** Smaller changes, a line each. */
  also: string[];
  illustration?: Illustration;
}

const RELEASES_URL = "https://github.com/vrppaul/claude-review/releases/tag";

/** The GitHub release a news entry points to for everything else in it. */
export function releaseUrl(release: string): string {
  return `${RELEASES_URL}/v${release}`;
}

export const RELEASE_NEWS: ReleaseNews[] = [
  {
    release: "1.5.0",
    title: "Paste a screenshot anywhere you write",
    body: "Ctrl+V puts an image into the panel, or into any comment, reply or edit. Claude gets it as a file it can open, and an image can be the whole question.",
    also: [
      "A short tour of the review, from the ? list whenever you want it.",
      "The panel waits for Claude to join instead of showing you setup commands.",
    ],
    illustration: { kind: "drawing", name: "pasted-screenshot" },
  },
];
