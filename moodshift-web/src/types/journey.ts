import { MoodSnapshot, TargetMood } from './mood';
import { JourneyTrack } from './track';

export enum JourneyStatus {
  PENDING = 'PENDING',
  ACTIVE = 'ACTIVE',
  PAUSED = 'PAUSED',
  COMPLETED = 'COMPLETED',
  ABANDONED = 'ABANDONED'
}

export interface JourneyPhase {
  id: string;
  name: string;                // "Settle In", "Build Momentum", "Reach Target"
  description: string;
  phaseNumber: 1 | 2 | 3;
  targetEnergyRange: [number, number];
  tracks: JourneyTrack[];
}

export interface MoodJourney {
  id: string;
  startMood: MoodSnapshot;
  targetMood: TargetMood;
  phases: JourneyPhase[];
  currentPhaseIndex: number;
  currentTrackIndex: number;
  createdAt: string;
  status: JourneyStatus;
  userRating?: number;         // 1 - 5 stars
  feedbackTag?: string;        // "Felt Energized", "Too intense", "Perfect transition"
}
