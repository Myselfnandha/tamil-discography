import { TargetMood } from '../types/mood';
import { Track } from '../types/track';

export class DynamicTempoController {
  public static readonly MIN_TEMPO = 0.96;
  public static readonly MAX_TEMPO = 1.04;
  public static readonly PITCH_INVARIANT = 1.0;

  public getPitchInvariant(): number {
    return DynamicTempoController.PITCH_INVARIANT;
  }

  /**
   * Calculates the track-specific tempo multiplier based on target mood and track BPM guardrails.
   * Guaranteed bounds: [0.96, 1.04]. Pitch invariant: strictly locked at 1.0.
   */
  public calculateTempo(target: TargetMood, track: Track, estimatedEnergy: number): number {
    const baseMultiplier = target.baseTempoMultiplier; // e.g. 1.04 for Energized, 0.96 for Wind Down
    const nativeBpm = track.tempoBpm;

    // Fallback: If native Spotify BPM is unknown, scale subtly by mood energy delta
    if (nativeBpm == null || isNaN(nativeBpm)) {
      const energyDelta = target.targetEnergy - estimatedEnergy;
      const dampened = 1.0 + (energyDelta * 0.04);
      return this.clamp(dampened);
    }

    const [idealMin, idealMax] = target.idealBpmRange;

    // BPM Guardrails: Prevent rushing fast songs or dragging slow songs
    let calculated = baseMultiplier;

    // Fast song in an upbeat mood (e.g. 150 BPM in Energized mode where ideal is 125-140)
    if (baseMultiplier > 1.0 && nativeBpm > idealMax) {
      const overshoot = Math.min(30, nativeBpm - idealMax) / 30; // 0.0 -> 1.0
      // Dampen speed boost towards 1.0
      calculated = 1.0 + ((baseMultiplier - 1.0) * (1.0 - overshoot * 0.75));
    }
    // Slow song in a relaxed mood (e.g. 50 BPM in Calm/Wind Down where ideal is 65-85)
    else if (baseMultiplier < 1.0 && nativeBpm < idealMin) {
      const undershoot = Math.min(30, idealMin - nativeBpm) / 30; // 0.0 -> 1.0
      // Dampen speed reduction towards 1.0 so it doesn't drag
      calculated = 1.0 - ((1.0 - baseMultiplier) * (1.0 - undershoot * 0.75));
    }

    return this.clamp(calculated);
  }

  private clamp(val: number): number {
    return Math.max(DynamicTempoController.MIN_TEMPO, Math.min(DynamicTempoController.MAX_TEMPO, Number(val.toFixed(3))));
  }
}

export const tempoController = new DynamicTempoController();
