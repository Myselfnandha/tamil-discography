import { describe, it, expect } from 'vitest';
import { journeyPlanner } from '../domain/JourneyPlanner';
import { MoodSnapshot, TargetMood, ModeConstraint, ScanSource, EmotionLabel, SignalType } from '../types/mood';
import { MOCK_TRACKS } from '../data/mockTracks';
import { DEFAULT_TARGET_MOODS } from '../data/defaultTargetMoods';

describe('JourneyPlanner', () => {
  const dummyStartMood: MoodSnapshot = {
    id: 'snap-1',
    energy: 0.25,
    valence: 0.25,
    arousal: 0.2,
    confidence: 0.9,
    isPersonalized: true,
    observedSignals: [SignalType.FACE_EXPRESSION, SignalType.DEVICE_USAGE],
    dominantEmotion: EmotionLabel.SAD,
    timestamp: new Date().toISOString(),
    source: ScanSource.AUTO_SENSE
  };

  const upliftTarget = DEFAULT_TARGET_MOODS.find(m => m.id === 'uplift')!;
  const catharticTarget = DEFAULT_TARGET_MOODS.find(m => m.id === 'cathartic')!;
  const calmTarget = DEFAULT_TARGET_MOODS.find(m => m.id === 'calm')!;

  it('generates a 3-phase journey playlist structure', () => {
    const journey = journeyPlanner.planJourney(dummyStartMood, upliftTarget, MOCK_TRACKS);

    expect(journey).toBeDefined();
    expect(journey.phases).toHaveLength(3);
    expect(journey.phases[0].name).toBe('Settle In');
    expect(journey.phases[1].name).toBe('Build Momentum');
    expect(journey.phases[2].name).toBe('Reach Target');

    // Total tracks: 2 (P1) + 3 (P2) + 3 (P3) = 8
    const totalTracks = journey.phases.reduce((acc, p) => acc + p.tracks.length, 0);
    expect(totalTracks).toBe(8);
  });

  it('enforces STRICT_MAJOR mode filtering in Phase 3 for Uplift', () => {
    const journey = journeyPlanner.planJourney(dummyStartMood, upliftTarget, MOCK_TRACKS);
    const phase3 = journey.phases[2];

    expect(upliftTarget.phase3ModeConstraint).toBe(ModeConstraint.STRICT_MAJOR);
    // Every track in Phase 3 with known musicalMode must be Major (mode === 1)
    phase3.tracks.forEach(t => {
      if (t.track.musicalMode != null) {
        expect(t.track.musicalMode).toBe(1);
      }
    });
  });

  it('enforces STRICT_MINOR mode filtering in Phase 3 for Cathartic', () => {
    const journey = journeyPlanner.planJourney(dummyStartMood, catharticTarget, MOCK_TRACKS);
    const phase3 = journey.phases[2];

    expect(catharticTarget.phase3ModeConstraint).toBe(ModeConstraint.STRICT_MINOR);
    // Every track in Phase 3 with known musicalMode must be Minor (mode === 0)
    phase3.tracks.forEach(t => {
      if (t.track.musicalMode != null) {
        expect(t.track.musicalMode).toBe(0);
      }
    });
  });

  it('allows ANY mode in Phase 3 for Calm/Focus targets', () => {
    const journey = journeyPlanner.planJourney(dummyStartMood, calmTarget, MOCK_TRACKS);
    const phase3 = journey.phases[2];

    expect(calmTarget.phase3ModeConstraint).toBe(ModeConstraint.ANY);
    expect(phase3.tracks.length).toBeGreaterThan(0);
  });

  it('computes dynamic tempo multipliers clamped to [0.96, 1.04] for every track', () => {
    const journey = journeyPlanner.planJourney(dummyStartMood, upliftTarget, MOCK_TRACKS);

    journey.phases.forEach(phase => {
      phase.tracks.forEach(jTrack => {
        expect(jTrack.targetTempoMultiplier).toBeGreaterThanOrEqual(0.96);
        expect(jTrack.targetTempoMultiplier).toBeLessThanOrEqual(1.04);
      });
    });
  });
});
