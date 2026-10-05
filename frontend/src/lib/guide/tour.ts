/**
 * The tour of a review, as data: where to look, what to say, and what the
 * reader does to move on.
 *
 * Steps point at the interface by its `data-tour` names — an attribute of
 * its own, so the tour and the tests can each rename what they need without
 * breaking the other — and light whichever of their targets is on screen. A
 * step with nothing on screen to show is passed over, which is how one tour
 * fits a diff, a plan and a transcript, with an agent attached or without.
 */

/** Where a comment went when the reader chose. */
export type CommentRoute = "review" | "ask";

/** One way a choice can go, as the card lays it out beside the others. */
export interface ForkOption {
  label: string;
  primary: boolean;
  says: string;
}

/** What the tour knows about the review it is showing. */
export interface TourContext {
  attached: boolean;
  route: CommentRoute;
}

/**
 * What the reader does to move on, when "Next" is not the way. Comment
 * fields say what happened to them; the tour never guesses from the page.
 */
export type WaitsFor =
  | { kind: "comment-opened"; hint: string }
  | {
      kind: "comment-sent";
      /** The routes this review offers; closing the field instead goes back. */
      routes: CommentRoute[];
      hint: string;
    };

export interface TourStep {
  id: string;
  /** Elements to light, by `data-tour` name; the light covers those on screen. */
  targets: string[];
  title: string;
  body: string;
  fork?: ForkOption[];
  waitsFor?: WaitsFor;
  /** Whether the step belongs in this review at all. */
  applies?: (context: TourContext) => boolean;
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: "review-base",
    targets: ["review-base", "review-base-list"],
    title: "What you are reviewing",
    body: "The changes Claude asked you to read. Open this to read the same work against something else: the start of an earlier round, to see only what Claude changed since, or any branch or tag. The threads stay where they are.",
  },
  {
    id: "files",
    targets: ["file-tree"],
    title: "Everything that changed",
    body: "Each file, with what it added and removed. Mark one viewed when you are through with it; a file Claude rewrites later loses that mark.",
  },
  {
    id: "comment-line",
    targets: ["line-number"],
    title: "Comment on a line",
    body: "Click a line number to comment there, or drag across numbers for a range. A screenshot pasted with Ctrl+V goes with the comment.",
    waitsFor: {
      kind: "comment-opened",
      hint: "Your turn: click a line number",
    },
  },
  {
    id: "comment-route",
    targets: ["comment-field"],
    title: "Two ways a comment can go",
    body: "Write what should change. Then decide when Claude hears about it.",
    fork: [
      {
        label: "Add to review",
        primary: true,
        says: "Waits with your other comments. All of them go together when you send a round.",
      },
      {
        label: "Ask now",
        primary: false,
        says: "Goes to Claude at once, on its own. The answer lands in the thread while you read on.",
      },
    ],
    waitsFor: {
      kind: "comment-sent",
      routes: ["review", "ask"],
      hint: "Your turn: pick one in the comment",
    },
    applies: (context) => context.attached,
  },
  {
    id: "comment-save",
    targets: ["comment-field"],
    title: "Add it to the review",
    body: "Write what should change. It waits with your other comments, and all of them go to Claude together when you finish the review.",
    waitsFor: {
      kind: "comment-sent",
      routes: ["review"],
      hint: "Your turn: add it to the review",
    },
    applies: (context) => !context.attached,
  },
  {
    id: "added",
    targets: ["unsent-count"],
    title: "Added to the review",
    body: "It waits with your other comments, and the count went up. Claude hears about all of them together when you send; until then you can still edit or delete it.",
    applies: (context) => context.route === "review",
  },
  {
    id: "asked",
    targets: ["awaited-answer", "answer"],
    title: "Asked straight away",
    body: "It went to Claude on its own, now. The answer arrives in this thread while you keep reading. Nothing else was sent, and the review stays open.",
    applies: (context) => context.route === "ask",
  },
  {
    id: "unsent",
    targets: ["unsent-count"],
    title: "Nothing goes until you send it",
    body: "Comments added to the review wait here. The first number is what Claude has not seen yet; the second is everything in the review.",
    applies: (context) => context.route === "ask",
  },
  {
    id: "panel",
    targets: ["agent-panel", "agent-panel-toggle"],
    title: "Talk about the whole change",
    body: "The plan, the tests, a file nobody commented on: ask here rather than on a line. Claude answers in the panel while you keep reading.",
    applies: (context) => context.attached,
  },
  {
    id: "round-or-end",
    targets: ["send"],
    title: "A round, or the end",
    body: "This opens what you have written, with room for a summary. From there a review either goes on or finishes.",
    fork: [
      {
        label: "Send round",
        primary: true,
        says: "Claude answers and changes the code, the diff is taken again under your threads, and the review goes on.",
      },
      {
        label: "End review",
        primary: false,
        says: "Everything goes as the final review and this page is done. Claude works from it on its own.",
      },
    ],
    applies: (context) => context.attached,
  },
  {
    id: "finish",
    targets: ["send"],
    title: "Finish the review",
    body: "This opens what you have written, with room for a summary, and sends it all to Claude as one review. The page is done after that.",
    applies: (context) => !context.attached,
  },
];

/** The steps this review's tour takes, in order. */
export function stepsFor(context: TourContext): TourStep[] {
  return TOUR_STEPS.filter((step) => !step.applies || step.applies(context));
}
