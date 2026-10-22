import { EmotionLabel } from './mood';

export interface CalibrationStep {
  step: number;
  title: string;
  instruction: string;
  targetEmotion: EmotionLabel;
  durationSeconds: number;
}

export interface LightingProfile {
  avgBrightness: number;
  contrastRatio: number;
  isBacklit: boolean;
}

export interface PersonalFaceProfile {
  userId: string;
  calibratedAt: string;
  baselineNeutral: number[];
  baselineHappy: number[];
  baselineTired: number[];
  baselineSurprised: number[];
  lightingProfile: LightingProfile;
  personalThreshold: number;
  correctionCount: number;
}
