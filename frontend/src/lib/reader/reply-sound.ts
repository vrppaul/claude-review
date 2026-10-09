/**
 * A tick when an answer arrives, for those who want one.
 *
 * Off by default: a review is often read in a room with other people, and a
 * chime out of a browser tab startles more than it informs. On, it is one
 * short tick, and only while the review is in a background tab — the dot
 * and the count are enough when the thread is on screen.
 */

import type { Settings } from "$lib/reader/settings.svelte";

// One short sine tick: an A, quiet, and gone before it can be called a chime
const TICK_PITCH_HERTZ = 880;
const TICK_LOUDNESS = 0.04;
// An exponential fade cannot reach zero; this is as near as it needs to get
const TICK_FADED = 0.0001;
const TICK_FADES_WITHIN_SECONDS = 0.12;
// Stopped just after the fade, so it never ends on a click
const TICK_STOPS_AFTER_SECONDS = 0.13;

function tick(): void {
  const Sound = window.AudioContext ?? window.webkitAudioContext;
  if (!Sound) return;

  const context = new Sound();
  const tone = context.createOscillator();
  const level = context.createGain();

  tone.frequency.value = TICK_PITCH_HERTZ;
  tone.type = "sine";
  level.gain.setValueAtTime(TICK_LOUDNESS, context.currentTime);
  level.gain.exponentialRampToValueAtTime(
    TICK_FADED,
    context.currentTime + TICK_FADES_WITHIN_SECONDS,
  );

  tone.connect(level).connect(context.destination);
  tone.start();
  tone.stop(context.currentTime + TICK_STOPS_AFTER_SECONDS);
  tone.onended = () => context.close();
}

export class ReplySound {
  readonly #settings: Settings;

  constructor(settings: Settings) {
    this.#settings = settings;
  }

  /** Say that an answer landed, if the reader asked to be told out loud. */
  announce(): void {
    if (!this.#settings.current.sound_on_replies || !document.hidden) return;
    try {
      tick();
    } catch {
      // Autoplay policy, no output device: not worth breaking a review over
    }
  }
}
