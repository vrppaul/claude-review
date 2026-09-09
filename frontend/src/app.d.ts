/// <reference types="vite/client" />
/// <reference types="svelte" />

declare global {
  interface Window {
    /** Safari's older spelling, still the only one on some versions. */
    webkitAudioContext?: typeof AudioContext;
  }
}

export {};
