import { useState, useEffect, useRef, useCallback } from 'react';
import { MoodJourney } from '../types/journey';
import { JourneyTrack } from '../types/track';
import { TargetMood } from '../types/mood';
import { tempoController } from '../domain/DynamicTempoController';

export interface UseAudioPlayerReturn {
  journey: MoodJourney | null;
  currentTrack: JourneyTrack | null;
  currentPhaseNumber: number;
  isPlaying: boolean;
  progress: number;            // 0.0 to 1.0
  currentTime: number;         // seconds
  duration: number;            // seconds
  effectiveTempo: number;      // e.g. 1.03
  isTempoTuned: boolean;
  manualTempo: number | null;  // user override slider
  isCrossfading: boolean;
  startJourney: (newJourney: MoodJourney) => void;
  play: () => void;
  pause: () => void;
  togglePlay: () => void;
  nextTrack: () => void;
  previousTrack: () => void;
  seek: (ratio: number) => void;
  setManualTempo: (val: number | null) => void;
  toggleTempoTuning: () => void;
}

export function useAudioPlayer(activeTargetMood: TargetMood): UseAudioPlayerReturn {
  const [journey, setJourney] = useState<MoodJourney | null>(null);
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(180);
  const [isTempoTuned, setIsTempoTuned] = useState(true);
  const [manualTempo, setManualTempoState] = useState<number | null>(null);
  const [isCrossfading, setIsCrossfading] = useState(false);

  // Audio Context & Nodes for synthesized music & HTML5 playback
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const synthOscRef = useRef<OscillatorNode | null>(null);
  const synthGainRef = useRef<GainNode | null>(null);
  const timerRef = useRef<number | null>(null);

  const currentPhase = journey?.phases[currentPhaseIndex] || null;
  const currentTrack = currentPhase?.tracks[currentTrackIndex] || null;

  // Calculate effective tempo: manual override > dynamic tempo > 1.0
  const computedDynamicTempo = currentTrack
    ? tempoController.calculateTempo(
        activeTargetMood,
        currentTrack.track,
        currentPhase?.targetEnergyRange[0] || activeTargetMood.targetEnergy
      )
    : 1.0;

  const effectiveTempo = !isTempoTuned
    ? 1.0
    : manualTempo !== null
    ? manualTempo
    : computedDynamicTempo;

  // Initialize Web Audio API for harmonic previews
  const initSynth = useCallback(() => {
    try {
      if (!audioContextRef.current) {
        const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        audioContextRef.current = new AudioCtx();
      }
      if (audioContextRef.current.state === 'suspended') {
        audioContextRef.current.resume();
      }
    } catch {
      // AudioContext not permitted without user gesture
    }
  }, []);

  // Update playback rate & pitch invariant
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.preservesPitch = true; // Invariant: Pitch strictly locked at 1.0x
      audioRef.current.playbackRate = effectiveTempo;
    }
  }, [effectiveTempo]);

  // Track progress simulation
  useEffect(() => {
    if (isPlaying) {
      const interval = window.setInterval(() => {
        setCurrentTime(prev => {
          const next = prev + (0.5 * effectiveTempo);
          if (next >= duration) {
            handleTrackEnd();
            return 0;
          }
          return next;
        });
      }, 500);
      timerRef.current = interval;
      return () => clearInterval(interval);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, [isPlaying, effectiveTempo, duration]);

  const handleTrackEnd = useCallback(() => {
    if (!journey) return;
    const currentP = journey.phases[currentPhaseIndex];
    if (currentTrackIndex < currentP.tracks.length - 1) {
      triggerCrossfade(() => {
        setCurrentTrackIndex(prev => prev + 1);
        setCurrentTime(0);
      });
    } else if (currentPhaseIndex < journey.phases.length - 1) {
      triggerCrossfade(() => {
        setCurrentPhaseIndex(prev => prev + 1);
        setCurrentTrackIndex(0);
        setCurrentTime(0);
      });
    } else {
      setIsPlaying(false);
      setCurrentTime(0);
    }
  }, [journey, currentPhaseIndex, currentTrackIndex]);

  const triggerCrossfade = (onComplete: () => void) => {
    setIsCrossfading(true);
    // 1.5s crossfade window simulation
    window.setTimeout(() => {
      onComplete();
      window.setTimeout(() => {
        setIsCrossfading(false);
      }, 750);
    }, 750);
  };

  const startJourney = useCallback((newJourney: MoodJourney) => {
    initSynth();
    setJourney(newJourney);
    setCurrentPhaseIndex(0);
    setCurrentTrackIndex(0);
    setCurrentTime(0);
    setDuration(180);
    setIsPlaying(true);
  }, [initSynth]);

  const play = useCallback(() => {
    initSynth();
    setIsPlaying(true);
  }, [initSynth]);

  const pause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const togglePlay = useCallback(() => {
    if (isPlaying) pause();
    else play();
  }, [isPlaying, play, pause]);

  const nextTrack = useCallback(() => {
    if (!journey) return;
    const currentP = journey.phases[currentPhaseIndex];
    triggerCrossfade(() => {
      if (currentTrackIndex < currentP.tracks.length - 1) {
        setCurrentTrackIndex(prev => prev + 1);
      } else if (currentPhaseIndex < journey.phases.length - 1) {
        setCurrentPhaseIndex(prev => prev + 1);
        setCurrentTrackIndex(0);
      }
      setCurrentTime(0);
    });
  }, [journey, currentPhaseIndex, currentTrackIndex]);

  const previousTrack = useCallback(() => {
    if (!journey) return;
    triggerCrossfade(() => {
      if (currentTime > 5) {
        setCurrentTime(0);
      } else if (currentTrackIndex > 0) {
        setCurrentTrackIndex(prev => prev - 1);
        setCurrentTime(0);
      } else if (currentPhaseIndex > 0) {
        setCurrentPhaseIndex(prev => prev - 1);
        const prevPhase = journey.phases[currentPhaseIndex - 1];
        setCurrentTrackIndex(prevPhase.tracks.length - 1);
        setCurrentTime(0);
      }
    });
  }, [journey, currentPhaseIndex, currentTrackIndex, currentTime]);

  const seek = useCallback((ratio: number) => {
    setCurrentTime(Math.max(0, Math.min(duration, ratio * duration)));
  }, [duration]);

  const setManualTempo = useCallback((val: number | null) => {
    setManualTempoState(val);
  }, []);

  const toggleTempoTuning = useCallback(() => {
    setIsTempoTuned(prev => !prev);
  }, []);

  const progress = duration > 0 ? Math.min(1.0, currentTime / duration) : 0;

  return {
    journey,
    currentTrack,
    currentPhaseNumber: currentPhaseIndex + 1,
    isPlaying,
    progress,
    currentTime,
    duration,
    effectiveTempo,
    isTempoTuned,
    manualTempo,
    isCrossfading,
    startJourney,
    play,
    pause,
    togglePlay,
    nextTrack,
    previousTrack,
    seek,
    setManualTempo,
    toggleTempoTuning
  };
}
