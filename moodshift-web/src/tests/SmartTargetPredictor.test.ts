import { describe, it, expect } from 'vitest';
import { smartPredictor } from '../domain/SmartTargetPredictor';
import { MoodSnapshot, SignalType, ScanSource, EmotionLabel } from '../types/mood';

describe('SmartTargetPredictor', () => {
  const baseMood: MoodSnapshot = {
    id: 'snap-1',
    energy: 0.5,
    valence: 0.5,
    arousal: 0.5,
    confidence: 0.8,
    isPersonalized: false,
    observedSignals: [SignalType.DEVICE_USAGE],
    dominantEmotion: EmotionLabel.NEUTRAL,
    timestamp: new Date().toISOString(),
    source: ScanSource.AUTO_SENSE
  };

  it('predicts contrasting mood boost when user is depleted and sad', () => {
    const lowMood: MoodSnapshot = {
      ...baseMood,
      energy: 0.2,
      valence: 0.2,
      dominantEmotion: EmotionLabel.SAD
    };

    const recommendation = smartPredictor.predict(lowMood);
    expect(recommendation).toBeDefined();
    expect(recommendation.recommended).toBeDefined();
    // When valence is low (<0.35) and energy is low (<0.35), Uplift or Energized should be recommended
    expect(['uplift', 'energized', 'cathartic']).toContain(recommendation.recommended.id);
  });

  it('predicts calm when user has high arousal/tension', () => {
    const tenseMood: MoodSnapshot = {
      ...baseMood,
      energy: 0.8,
      valence: 0.3,
      arousal: 0.9,
      dominantEmotion: EmotionLabel.ANGRY
    };

    const recommendation = smartPredictor.predict(tenseMood);
    expect(recommendation.recommended.id).toBe('calm');
    expect(recommendation.predictionReason).toContain('calm');
  });

  it('provides up to 3 alternative target moods', () => {
    const result = smartPredictor.predict(baseMood);
    expect(result.alternatives).toBeDefined();
    expect(result.alternatives.length).toBeGreaterThanOrEqual(1);
    expect(result.alternatives.length).toBeLessThanOrEqual(3);
  });

  it('predictTargetMood convenience method returns the top recommended TargetMood object', () => {
    const top = smartPredictor.predictTargetMood(baseMood);
    expect(top).toBeDefined();
    expect(top.id).toBeDefined();
    expect(top.baseTempoMultiplier).toBeGreaterThanOrEqual(0.96);
    expect(top.baseTempoMultiplier).toBeLessThanOrEqual(1.04);
  });
});
