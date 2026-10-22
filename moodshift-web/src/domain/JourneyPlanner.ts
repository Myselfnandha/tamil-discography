import { MoodSnapshot, TargetMood, ModeConstraint } from '../types/mood';
import { Track, JourneyTrack, PlaybackSource } from '../types/track';
import { MoodJourney, JourneyPhase, JourneyStatus } from '../types/journey';
import { camelotEngine } from './CamelotHarmonicEngine';
import { tempoController } from './DynamicTempoController';

export class JourneyPlanner {
  /**
   * Builds an adaptive 3-phase journey playlist from candidate tracks.
   */
  public planJourney(
    startMood: MoodSnapshot,
    targetMood: TargetMood,
    availableTracks: Track[]
  ): MoodJourney {
    const journeyId = `journey_${Date.now()}`;
    const usedTrackIds = new Set<string>();

    // 1. Phase 1: SETTLE IN (2 tracks)
    const phase1Tracks = this.selectTracksForPhase(
      1,
      'Settle In',
      'Honoring your current headspace with familiar comfort sounds.',
      [startMood.energy - 0.1, startMood.energy + 0.1],
      startMood.energy,
      startMood.valence,
      targetMood,
      availableTracks,
      usedTrackIds,
      null,
      2,
      false
    );

    // 2. Phase 2: BUILD MOMENTUM (3 tracks)
    const lastP1Track = phase1Tracks[phase1Tracks.length - 1]?.track;
    const midEnergy = (startMood.energy + targetMood.targetEnergy) / 2;
    const midValence = (startMood.valence + targetMood.targetValence) / 2;

    const phase2Tracks = this.selectTracksForPhase(
      2,
      'Build Momentum',
      'Subtle harmonic elevation bridging where you are to where you want to be.',
      [Math.min(startMood.energy, targetMood.targetEnergy), Math.max(startMood.energy, targetMood.targetEnergy)],
      midEnergy,
      midValence,
      targetMood,
      availableTracks,
      usedTrackIds,
      lastP1Track,
      3,
      false
    );

    // 3. Phase 3: REACH TARGET (3 tracks - Strict Mode Filter enforced)
    const lastP2Track = phase2Tracks[phase2Tracks.length - 1]?.track;
    const phase3Tracks = this.selectTracksForPhase(
      3,
      'Reach Target',
      `Locked into your desired ${targetMood.name} state with resonant tonality.`,
      [targetMood.targetEnergy - 0.1, targetMood.targetEnergy + 0.1],
      targetMood.targetEnergy,
      targetMood.targetValence,
      targetMood,
      availableTracks,
      usedTrackIds,
      lastP2Track,
      3,
      true // isFinalPhase -> enforces strict mode filtering
    );

    const phases: JourneyPhase[] = [
      {
        id: `${journeyId}_p1`,
        name: 'Settle In',
        description: 'Honoring your current headspace with familiar comfort sounds.',
        phaseNumber: 1,
        targetEnergyRange: [Math.max(0, startMood.energy - 0.1), Math.min(1, startMood.energy + 0.1)],
        tracks: phase1Tracks
      },
      {
        id: `${journeyId}_p2`,
        name: 'Build Momentum',
        description: 'Subtle harmonic elevation bridging where you are to where you want to be.',
        phaseNumber: 2,
        targetEnergyRange: [Math.min(startMood.energy, targetMood.targetEnergy), Math.max(startMood.energy, targetMood.targetEnergy)],
        tracks: phase2Tracks
      },
      {
        id: `${journeyId}_p3`,
        name: 'Reach Target',
        description: `Locked into your desired ${targetMood.name} state with resonant tonality.`,
        phaseNumber: 3,
        targetEnergyRange: [Math.max(0, targetMood.targetEnergy - 0.1), Math.min(1, targetMood.targetEnergy + 0.1)],
        tracks: phase3Tracks
      }
    ];

    return {
      id: journeyId,
      startMood,
      targetMood,
      phases,
      currentPhaseIndex: 0,
      currentTrackIndex: 0,
      createdAt: new Date().toISOString(),
      status: JourneyStatus.ACTIVE
    };
  }

  private selectTracksForPhase(
    phaseNumber: 1 | 2 | 3,
    phaseName: string,
    _description: string,
    energyRange: [number, number],
    centerEnergy: number,
    centerValence: number,
    targetMood: TargetMood,
    allTracks: Track[],
    usedTrackIds: Set<string>,
    previousTrack: Track | null,
    count: number,
    isFinalPhase: boolean
  ): JourneyTrack[] {
    const selected: JourneyTrack[] = [];
    let currentPrev = previousTrack;

    for (let i = 0; i < count; i++) {
      // Score and rank available unused tracks
      const scoredCandidates = allTracks
        .filter(t => !usedTrackIds.has(t.id))
        .map(track => {
          const score = this.scoreTrack(track, centerEnergy, centerValence, targetMood, currentPrev, isFinalPhase);
          return { track, score };
        })
        .filter(item => item.score > -1) // -1 indicates hard rejection from strict mode filter
        .sort((a, b) => b.score - a.score);

      if (scoredCandidates.length === 0) {
        // Fallback: relax mode constraint if library exhausted
        const fallback = allTracks.find(t => !usedTrackIds.has(t.id)) || allTracks[0];
        if (!fallback) break;
        usedTrackIds.add(fallback.id);
        const tempo = tempoController.calculateTempo(targetMood, fallback, centerEnergy);
        selected.push({
          track: fallback,
          source: PlaybackSource.YOUTUBE_STREAM,
          estimatedEnergy: fallback.energy,
          estimatedValence: fallback.valence,
          targetTempoMultiplier: tempo,
          reason: `Phase ${phaseNumber} baseline match`
        });
        currentPrev = fallback;
        continue;
      }

      const best = scoredCandidates[0].track;
      usedTrackIds.add(best.id);

      const computedTempo = tempoController.calculateTempo(targetMood, best, centerEnergy);
      const harmonicBonus = currentPrev ? camelotEngine.calculateHarmonicBonus(currentPrev.camelotCode, best.camelotCode) : 0;
      
      let reason = `Phase ${phaseNumber}: Energy match (${best.energy.toFixed(2)})`;
      if (isFinalPhase && best.musicalMode === 1 && targetMood.phase3ModeConstraint === ModeConstraint.STRICT_MAJOR) {
        reason = `Destination Major Key anchor (${best.camelotCode || 'Major'})`;
      } else if (isFinalPhase && best.musicalMode === 0 && targetMood.phase3ModeConstraint === ModeConstraint.STRICT_MINOR) {
        reason = `Destination Minor Key anchor (${best.camelotCode || 'Minor'})`;
      } else if (harmonicBonus >= 0.10 && currentPrev) {
        reason = `Harmonic Camelot transition: ${currentPrev.camelotCode} → ${best.camelotCode}`;
      } else if (best.playCount > 5) {
        reason = `Familiar comfort track (${best.playCount} previous plays)`;
      }

      selected.push({
        track: best,
        source: PlaybackSource.YOUTUBE_STREAM,
        estimatedEnergy: best.energy,
        estimatedValence: best.valence,
        targetTempoMultiplier: computedTempo,
        reason
      });

      currentPrev = best;
    }

    return selected;
  }

  private scoreTrack(
    track: Track,
    targetEnergy: number,
    targetValence: number,
    targetMood: TargetMood,
    prevTrack: Track | null,
    isFinalPhase: boolean
  ): number {
    // 1. Phase 3 Strict Mode Filter (with unknown metadata tolerance)
    if (isFinalPhase && track.musicalMode != null) {
      if (targetMood.phase3ModeConstraint === ModeConstraint.STRICT_MAJOR && track.musicalMode !== 1) {
        return -1; // Strict rejection
      }
      if (targetMood.phase3ModeConstraint === ModeConstraint.STRICT_MINOR && track.musicalMode !== 0) {
        return -1; // Strict rejection
      }
    }

    // 2. Coordinate proximity
    const energyFit = 1.0 - Math.abs(track.energy - targetEnergy);
    const valenceFit = 1.0 - Math.abs(track.valence - targetValence);

    // 3. Camelot Circle-of-Fifths harmonic transition bonus
    const harmonicBonus = prevTrack ? camelotEngine.calculateHarmonicBonus(prevTrack.camelotCode, track.camelotCode) : 0;

    // 4. Intermediate phase mode affinity
    let modeAffinityBonus = 0;
    if (track.musicalMode != null) {
      if (targetMood.phase3ModeConstraint === ModeConstraint.STRICT_MAJOR && track.musicalMode === 1) {
        modeAffinityBonus = 0.10;
      } else if (targetMood.phase3ModeConstraint === ModeConstraint.STRICT_MINOR && track.musicalMode === 0) {
        modeAffinityBonus = 0.10;
      }
    }

    // 5. Familiarity bonus
    const familiarityBonus = track.playCount > 5 ? 0.10 : 0.0;

    return (energyFit * 0.35) + (valenceFit * 0.35) + (harmonicBonus * 0.15) + modeAffinityBonus + familiarityBonus;
  }
}

export const journeyPlanner = new JourneyPlanner();
