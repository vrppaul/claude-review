/**
 * What the server said was wrong with a request, in words the reader can act on.
 *
 * Falls back to what was being done and the status when the server said
 * nothing usable: a bare number is the last resort, not the message.
 */
export async function refusalOf(
  response: Response,
  doing: string,
): Promise<string> {
  try {
    const said: { detail?: unknown } = await response.json();
    if (typeof said.detail === "string") return said.detail;
  } catch {
    // Not JSON: the status is all there is
  }
  return `${doing}: ${response.status}`;
}
