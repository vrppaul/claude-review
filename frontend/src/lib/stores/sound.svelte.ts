/**
 * A tick when an answer arrives, for those who want one.
 *
 * Off by default: a review is often read in a room with other people, and a
 * chime out of a browser tab startles more than it informs. On, it is one
 * short tick, and only while the review is in a background tab — the dot
 * and the count are enough when the thread is on screen.
 */

import { settingsStore } from "$lib/stores/settings.svelte";

function tick(): void {
  const Sound = window.AudioContext ?? window.webkitAudioContext;
  if (!Sound) return;

  const context = new Sound();
  const tone = context.createOscillator();
  const level = context.createGain();

  tone.frequency.value = 880;
  tone.type = "sine";
  // Quiet, and gone before it can be called a chime
  level.gain.setValueAtTime(0.04, context.currentTime);
  level.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.12);

  tone.connect(level).connect(context.destination);
  tone.start();
  tone.stop(context.currentTime + 0.13);
  tone.onended = () => context.close();
}

export const soundStore = {
  get enabled(): boolean {
    return settingsStore.settings.sound_on_replies;
  },

  setEnabled(enabled: boolean) {
    void settingsStore.change({ sound_on_replies: enabled });
  },

  /** Say that an answer landed, if the reader asked to be told out loud. */
  announce() {
    if (!settingsStore.settings.sound_on_replies || !document.hidden) return;
    try {
      tick();
    } catch {
      // Autoplay policy, no output device: not worth breaking a review over
    }
  },
};
