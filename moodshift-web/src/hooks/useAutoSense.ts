import { useState, useEffect, useCallback } from 'react';
import { MoodSnapshot, SignalType, ScanSource } from '../types/mood';
import { moodFuser, RawMoodSignal } from '../domain/MoodFuser';
import { smartTargetPredictor, RankedTargetMoods } from '../domain/SmartTargetPredictor';

export interface UseAutoSenseReturn {
  isAutoSensing: boolean;
  isScanning: boolean;
  currentMood: MoodSnapshot;
  rankedTargets: RankedTargetMoods;
  refreshAutoSense: () => void;
  refreshScan: () => void;
  updateUserReport: (energy: number, valence: number) => void;
}

const defaultFaceSignal = (): RawMoodSignal => ({
  type: SignalType.FACE_EXPRESSION,
  energy: 0.35,
  valence: 0.40,
  arousal: 0.30,
  confidence: 0.70,
  isAvailable: true
});

export function useAutoSense(
  getFaceSignal?: () => RawMoodSignal,
  hasPersonalProfile: boolean = false
): UseAutoSenseReturn {
  const [isAutoSensing, setIsAutoSensing] = useState(true);
  const faceSignalFn = getFaceSignal || defaultFaceSignal;

  // Initialize with realistic sensed state
  const [currentMood, setCurrentMood] = useState<MoodSnapshot>(() => {
    return {
      id: 'init_snapshot',
      energy: 0.28,
      valence: 0.34,
      arousal: 0.32,
      confidence: 0.88,
      isPersonalized: hasPersonalProfile,
      observedSignals: [SignalType.FACE_EXPRESSION, SignalType.DEVICE_USAGE],
      dominantEmotion: null,
      timestamp: new Date().toISOString(),
      source: ScanSource.AUTO_SENSE
    };
  });

  const [rankedTargets, setRankedTargets] = useState<RankedTargetMoods>(() => {
    return smartTargetPredictor.predict(currentMood);
  });

  const runSense = useCallback(() => {
    setIsAutoSensing(true);
    // Simulate passive 1.5s background scan
    const timer = window.setTimeout(() => {
      const faceSig = faceSignalFn();

      // Device usage heuristic (unlock frequency, time of day)
      const hour = new Date().getHours();
      const deviceSig: RawMoodSignal = {
        type: SignalType.DEVICE_USAGE,
        energy: hour < 12 ? 0.35 : 0.45,
        valence: 0.48,
        arousal: 0.38,
        confidence: 0.65,
        isAvailable: true
      };

      const fused = moodFuser.fuse([faceSig, deviceSig], hasPersonalProfile, ScanSource.AUTO_SENSE);
      setCurrentMood(fused);
      setRankedTargets(smartTargetPredictor.predict(fused));
      setIsAutoSensing(false);
    }, 1500);

    return () => clearTimeout(timer);
  }, [getFaceSignal, hasPersonalProfile]);

  useEffect(() => {
    const cancel = runSense();
    return cancel;
  }, [runSense]);

  const updateUserReport = useCallback((energy: number, valence: number) => {
    const reportSig: RawMoodSignal = {
      type: SignalType.SELF_REPORT,
      energy,
      valence,
      arousal: (energy + (1 - valence)) / 2,
      confidence: 0.98,
      isAvailable: true
    };
    const faceSig = faceSignalFn();
    const fused = moodFuser.fuse([reportSig, faceSig], hasPersonalProfile, ScanSource.MANUAL);
    setCurrentMood(fused);
    setRankedTargets(smartTargetPredictor.predict(fused));
  }, [faceSignalFn, hasPersonalProfile]);

  return {
    isAutoSensing,
    isScanning: isAutoSensing,
    currentMood,
    rankedTargets,
    refreshAutoSense: runSense,
    refreshScan: runSense,
    updateUserReport
  };
}
