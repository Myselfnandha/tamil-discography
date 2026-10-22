import { MoodSnapshot, TargetMood } from '../types/mood';
import { DEFAULT_TARGET_MOODS } from '../data/defaultTargetMoods';

export interface RankedTargetMoods {
  recommended: TargetMood;
  alternatives: TargetMood[];
  predictionReason: string;
}

export class SmartTargetPredictor {
  public predict(currentMood: MoodSnapshot): RankedTargetMoods {
    const hour = new Date().getHours();
    const scores = new Map<string, { target: TargetMood; score: number; reason: string }>();

    DEFAULT_TARGET_MOODS.forEach(target => {
      scores.set(target.id, { target, score: 0.5, reason: 'Balanced baseline' });
    });

    // 1. Time-of-day contextual defaults
    if (hour >= 5 && hour < 9) {
      this.boost(scores, 'energized', 0.35, 'Early morning energy kickstart');
    } else if (hour >= 9 && hour < 13) {
      this.boost(scores, 'focus', 0.40, 'Peak morning focus & flow');
    } else if (hour >= 13 && hour < 17) {
      this.boost(scores, 'uplift', 0.35, 'Mid-day optimism & vitality');
    } else if (hour >= 17 && hour < 21) {
      this.boost(scores, 'calm', 0.35, 'Evening unwind & decompress');
    } else {
      this.boost(scores, 'wind_down', 0.45, 'Late night calm & restorative rest');
    }

    // 2. Mood-contrast heuristics (shift AWAY from negative/depleted states)
    if (currentMood.energy < 0.35) {
      this.boost(scores, 'energized', 0.40, 'Low energy detected — boost needed');
    }
    if (currentMood.valence < 0.35) {
      this.boost(scores, 'uplift', 0.45, 'Negative valence — brightening mood');
      this.boost(scores, 'cathartic', 0.30, 'Deep emotional release alternative');
    }
    if (currentMood.arousal > 0.75) {
      this.boost(scores, 'calm', 0.80, 'High arousal/tension — calming ground');
    }

    // Sort descending by score
    const sorted = Array.from(scores.values()).sort((a, b) => b.score - a.score);

    return {
      recommended: sorted[0].target,
      alternatives: sorted.slice(1, 4).map(s => s.target),
      predictionReason: sorted[0].reason
    };
  }

  public predictTargetMood(currentMood: MoodSnapshot): TargetMood {
    return this.predict(currentMood).recommended;
  }

  private boost(scores: Map<string, { target: TargetMood; score: number; reason: string }>, id: string, amount: number, reason: string): void {
    const entry = scores.get(id);
    if (entry) {
      entry.score += amount;
      entry.reason = reason;
    }
  }
}

export const smartTargetPredictor = new SmartTargetPredictor();
export const smartPredictor = smartTargetPredictor;
