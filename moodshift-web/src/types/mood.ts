export enum SignalType {
  FACE_EXPRESSION = 'FACE_EXPRESSION',
  DEVICE_USAGE = 'DEVICE_USAGE',
  SELF_REPORT = 'SELF_REPORT',
  APP_FEEDBACK = 'APP_FEEDBACK',
  MUSIC_HISTORY = 'MUSIC_HISTORY'
}

export enum EmotionLabel {
  HAPPY = 'HAPPY',
  SAD = 'SAD',
  ANGRY = 'ANGRY',
  SURPRISED = 'SURPRISED',
  FEARFUL = 'FEARFUL',
  DISGUSTED = 'DISGUSTED',
  NEUTRAL = 'NEUTRAL'
}

export enum CorrectionSource {
  USER_MANUAL = 'USER_MANUAL',
  USER_EMOJI_PICKER = 'USER_EMOJI_PICKER',
  SKIP_PATTERN = 'SKIP_PATTERN'
}

export enum ScanSource {
  MANUAL = 'MANUAL',
  AUTO_SENSE = 'AUTO_SENSE',
  WIDGET = 'WIDGET',
  APP_SHORTCUT = 'APP_SHORTCUT',
  ROUTINE = 'ROUTINE'
}

export enum ModeConstraint {
  STRICT_MAJOR = 'STRICT_MAJOR',
  STRICT_MINOR = 'STRICT_MINOR',
  ANY = 'ANY'
}

export enum FlowMode {
  AUTO = 'AUTO',       // Zero decisions, auto-play on open
  GUIDED = 'GUIDED',   // Ambient mood card with 1-tap start (Default)
  MANUAL = 'MANUAL'    // Full multi-step camera scan and diagnostic flow
}

export interface MoodCorrection {
  correctedBy: CorrectionSource;
  correctedEnergy: number | null;
  correctedValence: number | null;
  freeText?: string;
}

export interface MoodSnapshot {
  id: string;
  energy: number;          // 0.0 (depleted) -> 1.0 (electric)
  valence: number;         // 0.0 (negative) -> 1.0 (positive)
  arousal: number;         // 0.0 (calm/drowsy) -> 1.0 (excited/tense)
  confidence: number;      // 0.0 -> 1.0
  isPersonalized: boolean; // True if personal calibration baseline was applied
  observedSignals: SignalType[];
  dominantEmotion: EmotionLabel | null;
  timestamp: string;
  userCorrection?: MoodCorrection | null;
  source: ScanSource;
}

export interface TargetMood {
  id: string;
  name: string;
  targetEnergy: number;
  targetValence: number;
  targetArousal: number;
  baseTempoMultiplier: number;          // [0.96 .. 1.04], Pitch invariant: strictly locked at 1.0
  idealBpmRange: [number, number];      // [minBpm, maxBpm]
  phase3ModeConstraint: ModeConstraint; // STRICT_MAJOR, STRICT_MINOR, or ANY
  preferredTonality: string;            // e.g. "Bright / Euphoric Major"
  description: string;
  icon: string;                         // Lucide icon identifier
  colorAccent: string;                  // Hex color code (e.g. #06B6D4)
  secondaryColor: string;
}
