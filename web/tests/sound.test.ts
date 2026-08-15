import { afterEach, describe, expect, it, vi } from "vitest";

import { BLACK, WHITE } from "../src/game/rules";

class FakeAudioParam {
  value = 0;
  values: number[] = [];

  setValueAtTime(value: number) {
    this.value = value;
    this.values.push(value);
    return this;
  }

  exponentialRampToValueAtTime(value: number) {
    this.value = value;
    this.values.push(value);
    return this;
  }
}

class FakeAudioNode {
  connect<T>(destination: T): T {
    return destination;
  }
}

class FakeOscillator extends FakeAudioNode {
  frequency = new FakeAudioParam();
  type = "sine";
  started = false;
  stopped = false;

  start() { this.started = true; }
  stop() { this.stopped = true; }
}

class FakeGain extends FakeAudioNode {
  gain = new FakeAudioParam();
}

class FakeFilter extends FakeAudioNode {
  frequency = new FakeAudioParam();
  Q = new FakeAudioParam();
  type = "lowpass";
}

class FakeBufferSource extends FakeAudioNode {
  buffer: AudioBuffer | null = null;
  start() {}
}

class FakeBuffer {
  readonly sampleRate: number;
  private readonly data: Float32Array;

  constructor(frameCount: number, sampleRate: number) {
    this.sampleRate = sampleRate;
    this.data = new Float32Array(frameCount);
  }

  getChannelData() {
    return this.data;
  }
}

class FakeAudioContext {
  static latest: FakeAudioContext | null = null;
  readonly currentTime = 1;
  readonly destination = new FakeAudioNode();
  readonly sampleRate = 48_000;
  readonly state = "running";
  readonly oscillators: FakeOscillator[] = [];

  constructor() {
    FakeAudioContext.latest = this;
  }

  createOscillator() {
    const oscillator = new FakeOscillator();
    this.oscillators.push(oscillator);
    return oscillator;
  }

  createGain() { return new FakeGain(); }
  createBufferSource() { return new FakeBufferSource(); }
  createBiquadFilter() { return new FakeFilter(); }
  createBuffer(_channels: number, frameCount: number, sampleRate: number) {
    return new FakeBuffer(frameCount, sampleRate);
  }
  resume() { return Promise.resolve(); }
}

describe("Web Audio sound synthesis", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("schedules distinct black, white, and outcome tones after a user gesture", async () => {
    vi.stubGlobal("AudioContext", FakeAudioContext);
    const { playMoveSound, playOutcomeSound, unlockSound } = await import("../src/audio/sound");

    expect(unlockSound()).toBe(true);
    expect(playMoveSound(BLACK)).toBe(true);
    expect(playMoveSound(WHITE)).toBe(true);
    expect(playOutcomeSound(BLACK)).toBe(true);

    const frequencies = FakeAudioContext.latest?.oscillators.flatMap((oscillator) => [
      oscillator.frequency.value,
      ...oscillator.frequency.values,
    ]) ?? [];
    expect(frequencies).toContain(168);
    expect(frequencies).toContain(224);
    expect(frequencies).toContain(392);
    expect(frequencies).toContain(659.25);
  });
});
