import { describe, it, expect } from 'vitest';
import { DynamicTempoController, tempoController } from '../domain/DynamicTempoController';
import { TargetMood, ModeConstraint } from '../types/mood';
import { Track } from '../types/track';

describe('DynamicTempoController', () => {
  const dummyTargetMood: TargetMood = {
    id: 'uplift',
    name: 'Uplift',
    targetEnergy: 0.8,
    targetValence: 0.8,
    targetArousal: 0.7,
    baseTempoMultiplier: 1.03, // +3%
    idealBpmRange: [115, 128],
    phase3ModeConstraint: ModeConstraint.STRICT_MAJOR,
    preferredTonality: 'Major',
    description: 'Bright uplifting state',
    icon: 'Sun',
    colorAccent: '#F59E0B',
    secondaryColor: '#451A03'
  };

  const dummyTrack: Track = {
    id: 't1',
    title: 'Test Track',
    artist: 'Test Artist',
    durationMs: 180000,
    tempoBpm: 120,
    musicalKey: 0,
    musicalMode: 1,
    camelotCode: '8B',
    energy: 0.6,
    valence: 0.7,
    playCount: 10
  };

  it('preserves the pitch invariant strictly at 1.0x', () => {
    expect(tempoController.getPitchInvariant()).toBe(1.0);
  });

  it('clamps tempo strictly within [0.96, 1.04]', () => {
    // Extreme target multiplier 1.20 -> clamped to 1.04
    const extremeFast: TargetMood = {
      ...dummyTargetMood,
      baseTempoMultiplier: 1.20
    };
    const fastResult = tempoController.calculateTempo(extremeFast, dummyTrack, 0.5);
    expect(fastResult).toBeLessThanOrEqual(1.04);
    expect(fastResult).toBeGreaterThanOrEqual(0.96);

    // Extreme slow multiplier 0.80 -> clamped to 0.96
    const extremeSlow: TargetMood = {
      ...dummyTargetMood,
      baseTempoMultiplier: 0.80
    };
    const slowResult = tempoController.calculateTempo(extremeSlow, dummyTrack, 0.5);
    expect(slowResult).toBeGreaterThanOrEqual(0.96);
    expect(slowResult).toBeLessThanOrEqual(1.04);
  });

  it('dampens tempo boost on fast songs (>130 BPM) via dynamic guardrails', () => {
    const fastSong: Track = {
      ...dummyTrack,
      tempoBpm: 140
    };
    const normalSong: Track = {
      ...dummyTrack,
      tempoBpm: 110
    };

    const fastTempo = tempoController.calculateTempo(dummyTargetMood, fastSong, 0.5);
    const normalTempo = tempoController.calculateTempo(dummyTargetMood, normalSong, 0.5);

    // Fast song boost should be dampened compared to normal song
    expect(fastTempo).toBeLessThan(normalTempo);
    expect(fastTempo).toBeGreaterThanOrEqual(1.0);
  });

  it('dampens tempo reduction on slow songs (<70 BPM) via dynamic guardrails', () => {
    const slowTarget: TargetMood = {
      ...dummyTargetMood,
      baseTempoMultiplier: 0.96 // Slow down
    };
    const slowSong: Track = {
      ...dummyTrack,
      tempoBpm: 60
    };
    const normalSong: Track = {
      ...dummyTrack,
      tempoBpm: 100
    };

    const slowTempo = tempoController.calculateTempo(slowTarget, slowSong, 0.5);
    const normalTempo = tempoController.calculateTempo(slowTarget, normalSong, 0.5);

    // Slow song should cut less than normal song
    expect(slowTempo).toBeGreaterThan(normalTempo);
    expect(slowTempo).toBeLessThanOrEqual(1.0);
  });

  it('gracefully handles tracks with missing BPM using estimated energy', () => {
    const trackNoBpm: Track = {
      ...dummyTrack,
      tempoBpm: null
    };

    const tempo = tempoController.calculateTempo(dummyTargetMood, trackNoBpm, 0.5);
    expect(tempo).toBeGreaterThanOrEqual(0.96);
    expect(tempo).toBeLessThanOrEqual(1.04);
  });
});
