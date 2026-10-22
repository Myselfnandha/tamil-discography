import { describe, it, expect } from 'vitest';
import { moodFuser, RawMoodSignal } from '../domain/MoodFuser';
import { SignalType, EmotionLabel, ScanSource } from '../types/mood';

describe('MoodFuser', () => {
  it('returns balanced default snapshot when no signals are available', () => {
    const emptySignals: RawMoodSignal[] = [];
    const snapshot = moodFuser.fuse(emptySignals, false, ScanSource.AUTO_SENSE);

    expect(snapshot.energy).toBe(0.5);
    expect(snapshot.valence).toBe(0.5);
    expect(snapshot.dominantEmotion).toBe(EmotionLabel.NEUTRAL);
    expect(snapshot.observedSignals).toHaveLength(0);
    expect(snapshot.source).toBe(ScanSource.AUTO_SENSE);
  });

  it('weights signals accurately when fusing self-report and device usage', () => {
    const signals: RawMoodSignal[] = [
      {
        type: SignalType.SELF_REPORT,
        energy: 0.8,
        valence: 0.8,
        arousal: 0.7,
        confidence: 0.9,
        isAvailable: true,
        detectedEmotion: EmotionLabel.HAPPY
      },
      {
        type: SignalType.DEVICE_USAGE,
        energy: 0.4,
        valence: 0.5,
        arousal: 0.3,
        confidence: 0.6,
        isAvailable: true
      }
    ];

    const snapshot = moodFuser.fuse(signals, false, ScanSource.MANUAL);

    // Self-report weight (0.40) > Device weight (0.18), so energy will tilt toward 0.8
    expect(snapshot.energy).toBeGreaterThan(0.6);
    expect(snapshot.dominantEmotion).toBe(EmotionLabel.HAPPY);
    expect(snapshot.observedSignals).toContain(SignalType.SELF_REPORT);
    expect(snapshot.observedSignals).toContain(SignalType.DEVICE_USAGE);
  });

  it('amplifies face expression weight when personal profile is active', () => {
    const signals: RawMoodSignal[] = [
      {
        type: SignalType.FACE_EXPRESSION,
        energy: 0.9,
        valence: 0.9,
        arousal: 0.8,
        confidence: 0.9,
        isAvailable: true,
        detectedEmotion: EmotionLabel.HAPPY
      },
      {
        type: SignalType.SELF_REPORT,
        energy: 0.3,
        valence: 0.3,
        arousal: 0.2,
        confidence: 0.8,
        isAvailable: true
      }
    ];

    const standard = moodFuser.fuse(signals, false);
    const personalized = moodFuser.fuse(signals, true);

    // In personalized mode, face weight is 0.35 (vs 0.20 unpersonalized), so energy should be higher
    expect(personalized.energy).toBeGreaterThan(standard.energy);
    expect(personalized.isPersonalized).toBe(true);
  });
});
