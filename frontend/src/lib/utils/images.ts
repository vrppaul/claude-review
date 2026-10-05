/**
 * Images the reader pastes into a message for the agent.
 *
 * Each one goes to the server the moment it is pasted, so the composer
 * shows what the agent will get while the words are still being written,
 * and the message itself carries only ids.
 */

import { refusalOf } from "$lib/utils/refusal";

const BYTES_PER_MEGABYTE = 1024 * 1024;

/** Where the server hands a kept image back. */
export function imageUrl(imageId: string): string {
  return `/api/images/${encodeURIComponent(imageId)}`;
}

/** The images among what was pasted. */
export function imagesAmong(files: FileList | null | undefined): File[] {
  return Array.from(files ?? []).filter((file) =>
    file.type.startsWith("image/"),
  );
}

/** A limit in bytes, said the way the server says it. */
export function wholeMegabytes(bytes: number): number {
  return Math.floor(bytes / BYTES_PER_MEGABYTE);
}

/**
 * Keep an image on the server and return its id.
 *
 * The body is the image itself: there is one thing to send, and a form
 * would only wrap it.
 */
export async function uploadImage(image: Blob): Promise<string> {
  const response = await fetch("/api/images", {
    method: "POST",
    headers: { "Content-Type": image.type },
    body: image,
  });
  if (!response.ok) {
    throw new Error(await refusalOf(response, "Could not attach the image"));
  }
  const kept: { image_id: string } = await response.json();
  return kept.image_id;
}

/**
 * Let the server drop an image taken off the message before it was sent.
 *
 * Best effort: whatever is left behind goes with the review when it ends.
 */
export async function discardImage(imageId: string): Promise<void> {
  try {
    await fetch(imageUrl(imageId), { method: "DELETE" });
  } catch {
    // The review's workspace is removed at the end either way
  }
}
