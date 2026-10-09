/**
 * Every route the review's page asks of its server, one function each.
 *
 * Each answers what the route answers, typed as the server's schema names
 * it, and throws an `ApiError` carrying the server's reason when it refuses.
 * What a failure means for the page is decided by whoever called.
 */

import { call, read } from "$lib/api/request";
import type {
  AskRequest,
  CancelRequest,
  DiffResponse,
  FileWindowResponse,
  FollowRequest,
  FollowResponse,
  GuideChange,
  ImageResponse,
  KeptGuide,
  KeptSettings,
  MessageRequest,
  ReaderSettings,
  RetakeResponse,
  ReviewResponse,
  SettingsChange,
  SubmitRequest,
  SubmitResponse,
  VersionsResponse,
} from "$lib/types";

/** What the review is and where it stands: read as the page opens. */
export function readReview(): Promise<ReviewResponse> {
  return read({
    method: "GET",
    path: "/api/review",
    doing: "Could not open the review",
  });
}

/** Which diff is asked for: whose whitespace, and against which base. */
export interface DiffQuery {
  ignoreWhitespace: boolean;
  /** The key of the base, as the server named it; null for the review's own. */
  base: string | null;
}

/** Take the diff against a base, with whitespace counted or not. */
export function takeDiff({
  ignoreWhitespace,
  base,
}: DiffQuery): Promise<DiffResponse> {
  const query = new URLSearchParams();
  if (ignoreWhitespace) query.set("ignore_whitespace", "true");
  if (base !== null) query.set("base", base);
  const asked = query.toString();
  return read({
    method: "GET",
    path: asked ? `/api/diff?${asked}` : "/api/diff",
    doing: "Could not take the diff",
  });
}

/** Take the diff again, after the work a round asked for. */
export function retakeDiff(): Promise<RetakeResponse> {
  return read({
    method: "POST",
    path: "/api/retake",
    sent: {},
    doing: "Could not take the diff again",
  });
}

/** What the working tree can be compared against. */
export function offeredVersions(): Promise<VersionsResponse> {
  return read({
    method: "GET",
    path: "/api/versions",
    doing: "Could not list what this can be compared against",
  });
}

/** Lines of a file a hunk left out, from `start` to `end`. */
export function readFileWindow(
  path: string,
  start: number,
  end: number,
): Promise<FileWindowResponse> {
  const query = new URLSearchParams({
    path,
    start: String(start),
    end: String(end),
  });
  return read({
    method: "GET",
    path: `/api/file-window?${query}`,
    doing: `Could not read ${path}`,
  });
}

/** Where each anchor now hangs on the review's diff, in the order asked. */
export function followAnchors(request: FollowRequest): Promise<FollowResponse> {
  return read({
    method: "POST",
    path: "/api/anchors/follow",
    sent: request,
    doing: "Could not move the threads",
  });
}

/** Hand a question asked in a thread over to whoever is answering. */
export async function askInThread(request: AskRequest): Promise<void> {
  await call({
    method: "POST",
    path: "/api/ask",
    sent: request,
    doing: "Could not ask",
  });
}

/** Send what has been written: a round, or the end of the review. */
export function submitReview(request: SubmitRequest): Promise<SubmitResponse> {
  return read({
    method: "POST",
    path: "/api/submit",
    sent: request,
    doing: "Could not send the review",
  });
}

/** End a review that was worked through in rounds. */
export async function endReview(): Promise<void> {
  await call({
    method: "POST",
    path: "/api/end",
    sent: {},
    doing: "Could not end the review",
  });
}

/** Send a message from the agent panel. */
export async function sendMessage(request: MessageRequest): Promise<void> {
  await call({
    method: "POST",
    path: "/api/message",
    sent: request,
    doing: "Could not send",
  });
}

/** Take back a message the agent has not answered yet. */
export async function cancelMessage(request: CancelRequest): Promise<void> {
  await call({
    method: "POST",
    path: "/api/cancel",
    sent: request,
    doing: "Could not stop it",
  });
}

/** Where the server hands a kept image back. */
export function imageUrl(imageId: string): string {
  return `/api/images/${encodeURIComponent(imageId)}`;
}

/** Keep an image on the server, the image itself as the body, and say what it is called. */
export function keepImage(image: Blob): Promise<ImageResponse> {
  return read({
    method: "POST",
    path: "/api/images",
    sent: image,
    doing: "Could not attach the image",
  });
}

/** Let the server drop an image taken off before it was sent. */
export async function discardImage(imageId: string): Promise<void> {
  await call({
    method: "DELETE",
    path: imageUrl(imageId),
    doing: "Could not drop the image",
  });
}

/** The reader's settings, and whether any were kept yet. */
export function readSettings(): Promise<KeptSettings> {
  return read({
    method: "GET",
    path: "/api/settings",
    doing: "Could not read the settings",
  });
}

/** Keep these choices for every later review, and say what the settings now are. */
export function keepSettings(changes: SettingsChange): Promise<ReaderSettings> {
  return read({
    method: "PUT",
    path: "/api/settings",
    sent: changes,
    doing: "Could not keep the settings",
  });
}

/** How far the reader has been shown around, and whether that was kept yet. */
export function readGuide(): Promise<KeptGuide> {
  return read({
    method: "GET",
    path: "/api/guide",
    doing: "Could not read what was shown",
  });
}

/** Keep how far the reader has been shown around. */
export async function keepGuide(change: GuideChange): Promise<void> {
  await call({
    method: "PUT",
    path: "/api/guide",
    sent: change,
    doing: "Could not remember what was shown",
  });
}
