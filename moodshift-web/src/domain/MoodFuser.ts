import { MoodSnapshot, SignalType, EmotionLabel, ScanSource } from '../types/mood';

export interface RawMoodSignal {
  type: SignalType;
  energy: number;
  valence: number;
  arousal: number;
  confidence: number;
  isAvailable: boolean;
  detectedEmotion?: EmotionLabel;
}

export class MoodFuser {
  /**
   * Fuses multi-source signals into a unified MoodSnapshot.
   * If user has a personal face profile, face expression gets a higher weight (0.35 vs 0.20).
   */
  public fuse(signals: RawMoodSignal[], hasPersonalProfile: boolean = false, source: ScanSource = ScanSource.MANUAL): MoodSnapshot {
    const weights: Record<SignalType, number> = hasPersonalProfile
      ? {
          [SignalType.SELF_REPORT]: 0.30,
          [SignalType.FACE_EXPRESSION]: 0.35,
          [SignalType.DEVICE_USAGE]: 0.15,
          [SignalType.APP_FEEDBACK]: 0.15,
          [SignalType.MUSIC_HISTORY]: 0.05
        }
      : {
          [SignalType.SELF_REPORT]: 0.40,
          [SignalType.FACE_EXPRESSION]: 0.20,
          [SignalType.DEVICE_USAGE]: 0.18,
          [SignalType.APP_FEEDBACK]: 0.17,
          [SignalType.MUSIC_HISTORY]: 0.05
        };

    const available = signals.filter(s => s.isAvailable);

    if (available.length === 0) {
      // Neutral default fallback
      return {
        id: `snap_${Date.now()}`,
        energy: 0.5,
        valence: 0.5,
        arousal: 0.4,
        confidence: 0.3,
        isPersonalized: hasPersonalProfile,
        observedSignals: [],
        dominantEmotion: EmotionLabel.NEUTRAL,
        timestamp: new Date().toISOString(),
        source
      };
    }

    const totalWeight = available.reduce((acc, s) => acc + (weights[s.type] || 0.1), 0);
    const energy = available.reduce((acc, s) => acc + s.energy * (weights[s.type] || 0.1), 0) / totalWeight;
    const valence = available.reduce((acc, s) => acc + s.valence * (weights[s.type] || 0.1), 0) / totalWeight;
    const arousal = available.reduce((acc, s) => acc + s.arousal * (weights[s.type] || 0.1), 0) / totalWeight;

    // Overall confidence calculation
    const avgSignalConf = available.reduce((acc, s) => acc + s.confidence, 0) / available.length;
    const confidence = Math.min(1.0, (avgSignalConf * 0.7) + (available.length >= 2 ? 0.3 : 0.1));

    // Extract dominant emotion from face or self-report
    const faceSignal = available.find(s => s.type === SignalType.FACE_EXPRESSION || s.type === SignalType.SELF_REPORT);
    const dominantEmotion = faceSignal?.detectedEmotion || this.inferEmotion(energy, valence);

    return {
      id: `snap_${Date.now()}`,
      energy: Number(energy.toFixed(3)),
      valence: Number(valence.toFixed(3)),
      arousal: Number(arousal.toFixed(3)),
      confidence: Number(confidence.toFixed(2)),
      isPersonalized: hasPersonalProfile,
      observedSignals: available.map(s => s.type),
      dominantEmotion,
      timestamp: new Date().toISOString(),
      source
    };
  }

  private inferEmotion(energy: number, valence: number): EmotionLabel {
    if (energy > 0.6 && valence > 0.6) return EmotionLabel.HAPPY;
    if (energy < 0.4 && valence < 0.4) return EmotionLabel.SAD;
    if (energy > 0.6 && valence < 0.3) return EmotionLabel.ANGRY;
    if (energy > 0.7 && valence > 0.5) return EmotionLabel.SURPRISED;
    return EmotionLabel.NEUTRAL;
  }
}

export const moodFuser = new MoodFuser();
