import { BLACK, DRAW, type Stone, type Winner } from "../game/rules";

let audioContext: AudioContext | null = null;
let noiseBuffer: AudioBuffer | null = null;
let userGestureSeen = false;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined" || typeof window.AudioContext === "undefined") {
    return null;
  }
  if (!audioContext) {
    try {
      audioContext = new window.AudioContext({ latencyHint: "interactive" });
    } catch {
      return null;
    }
  }
  return audioContext;
}

function runWhenReady(play: (context: AudioContext) => void): boolean {
  if (!userGestureSeen) {
    return false;
  }
  const context = getAudioContext();
  if (!context) {
    return false;
  }
  if (context.state === "suspended") {
    void context.resume().then(() => play(context)).catch(() => undefined);
  } else {
    play(context);
  }
  return true;
}

export function unlockSound(): boolean {
  userGestureSeen = true;
  const context = getAudioContext();
  if (!context) {
    return false;
  }
  if (context.state === "suspended") {
    void context.resume().catch(() => undefined);
  }
  return true;
}

function getNoiseBuffer(context: AudioContext): AudioBuffer {
  if (noiseBuffer && noiseBuffer.sampleRate === context.sampleRate) {
    return noiseBuffer;
  }
  const frameCount = Math.floor(context.sampleRate * 0.035);
  noiseBuffer = context.createBuffer(1, frameCount, context.sampleRate);
  const channel = noiseBuffer.getChannelData(0);
  for (let index = 0; index < frameCount; index += 1) {
    const envelope = 1 - index / frameCount;
    channel[index] = (Math.random() * 2 - 1) * envelope;
  }
  return noiseBuffer;
}

function scheduleMoveSound(context: AudioContext, stone: Stone) {
  const start = context.currentTime + 0.006;
  const isBlack = stone === BLACK;

  const body = context.createOscillator();
  const bodyGain = context.createGain();
  body.type = "triangle";
  body.frequency.setValueAtTime(isBlack ? 168 : 224, start);
  body.frequency.exponentialRampToValueAtTime(isBlack ? 88 : 118, start + 0.11);
  bodyGain.gain.setValueAtTime(isBlack ? 0.115 : 0.095, start);
  bodyGain.gain.exponentialRampToValueAtTime(0.0001, start + 0.13);
  body.connect(bodyGain).connect(context.destination);
  body.start(start);
  body.stop(start + 0.14);

  const impact = context.createBufferSource();
  const impactFilter = context.createBiquadFilter();
  const impactGain = context.createGain();
  impact.buffer = getNoiseBuffer(context);
  impactFilter.type = "bandpass";
  impactFilter.frequency.value = isBlack ? 720 : 980;
  impactFilter.Q.value = 0.9;
  impactGain.gain.setValueAtTime(isBlack ? 0.075 : 0.06, start);
  impactGain.gain.exponentialRampToValueAtTime(0.0001, start + 0.045);
  impact.connect(impactFilter).connect(impactGain).connect(context.destination);
  impact.start(start);
}

export function playMoveSound(stone: Stone): boolean {
  return runWhenReady((context) => scheduleMoveSound(context, stone));
}

export function playOutcomeSound(winner: Exclude<Winner, null>): boolean {
  return runWhenReady((context) => {
    const frequencies = winner === DRAW ? [294, 247] : [392, 523.25, 659.25];
    const start = context.currentTime + 0.16;
    frequencies.forEach((frequency, index) => {
      const noteStart = start + index * 0.085;
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(0.0001, noteStart);
      gain.gain.exponentialRampToValueAtTime(0.08, noteStart + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, noteStart + 0.19);
      oscillator.connect(gain).connect(context.destination);
      oscillator.start(noteStart);
      oscillator.stop(noteStart + 0.2);
    });
  });
}

export function playEnabledSound(): boolean {
  return runWhenReady((context) => {
    const start = context.currentTime + 0.01;
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(440, start);
    oscillator.frequency.exponentialRampToValueAtTime(587.33, start + 0.08);
    gain.gain.setValueAtTime(0.045, start);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.11);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(start);
    oscillator.stop(start + 0.12);
  });
}
