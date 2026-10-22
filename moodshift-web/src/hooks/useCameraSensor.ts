import { useState, useEffect, useRef, useCallback } from 'react';
import { EmotionLabel, SignalType } from '../types/mood';
import { RawMoodSignal } from '../domain/MoodFuser';
import { PersonalFaceProfile } from '../types/face';

export interface UseCameraSensorReturn {
  hasCameraPermission: boolean;
  isStreaming: boolean;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  detectedEmotion: EmotionLabel;
  detectedConfidence: number;
  personalProfile: PersonalFaceProfile | null;
  isCalibrating: boolean;
  calibrationStep: number;
  requestCamera: () => Promise<boolean>;
  stopCamera: () => void;
  startCalibration: () => void;
  advanceCalibration: () => void;
  cancelCalibration: () => void;
  simulateEmotion: (emotion: EmotionLabel) => void;
  getFaceSignal: () => RawMoodSignal;
}

const EMOTION_COORDINATES: Record<EmotionLabel, { energy: number; valence: number; arousal: number }> = {
  [EmotionLabel.HAPPY]: { energy: 0.75, valence: 0.85, arousal: 0.65 },
  [EmotionLabel.SAD]: { energy: 0.20, valence: 0.22, arousal: 0.30 },
  [EmotionLabel.ANGRY]: { energy: 0.80, valence: 0.15, arousal: 0.88 },
  [EmotionLabel.SURPRISED]: { energy: 0.72, valence: 0.60, arousal: 0.80 },
  [EmotionLabel.FEARFUL]: { energy: 0.50, valence: 0.20, arousal: 0.80 },
  [EmotionLabel.DISGUSTED]: { energy: 0.40, valence: 0.15, arousal: 0.50 },
  [EmotionLabel.NEUTRAL]: { energy: 0.50, valence: 0.50, arousal: 0.35 }
};

export function useCameraSensor(): UseCameraSensorReturn {
  const [hasCameraPermission, setHasCameraPermission] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [detectedEmotion, setDetectedEmotion] = useState<EmotionLabel>(EmotionLabel.NEUTRAL);
  const [detectedConfidence, setDetectedConfidence] = useState(0.85);
  const [personalProfile, setPersonalProfile] = useState<PersonalFaceProfile | null>(() => {
    try {
      const saved = localStorage.getItem('moodshift_face_profile');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [isCalibrating, setIsCalibrating] = useState(false);
  const [calibrationStep, setCalibrationStep] = useState(1);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const requestCamera = useCallback(async (): Promise<boolean> => {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }
        setHasCameraPermission(true);
        setIsStreaming(true);
        return true;
      }
      return false;
    } catch (err) {
      console.warn('Camera access denied or unavailable, utilizing face sensor simulator:', err);
      setHasCameraPermission(false);
      setIsStreaming(false);
      return false;
    }
  }, []);

  const startCalibration = useCallback(() => {
    setIsCalibrating(true);
    setCalibrationStep(1);
    requestCamera();
  }, [requestCamera]);

  const advanceCalibration = useCallback(() => {
    if (calibrationStep < 5) {
      setCalibrationStep(prev => prev + 1);
    } else {
      // Completed calibration! Save profile to localStorage
      const mockProfile: PersonalFaceProfile = {
        userId: 'user_local_1',
        calibratedAt: new Date().toISOString(),
        baselineNeutral: Array.from({ length: 128 }, () => Math.random()),
        baselineHappy: Array.from({ length: 128 }, () => Math.random()),
        baselineTired: Array.from({ length: 128 }, () => Math.random()),
        baselineSurprised: Array.from({ length: 128 }, () => Math.random()),
        lightingProfile: { avgBrightness: 0.72, contrastRatio: 0.85, isBacklit: false },
        personalThreshold: 0.82,
        correctionCount: 0
      };
      setPersonalProfile(mockProfile);
      localStorage.setItem('moodshift_face_profile', JSON.stringify(mockProfile));
      setIsCalibrating(false);
      setCalibrationStep(1);
    }
  }, [calibrationStep]);

  const cancelCalibration = useCallback(() => {
    setIsCalibrating(false);
    setCalibrationStep(1);
    stopCamera();
  }, [stopCamera]);

  const simulateEmotion = useCallback((emotion: EmotionLabel) => {
    setDetectedEmotion(emotion);
    setDetectedConfidence(0.92);
  }, []);

  const getFaceSignal = useCallback((): RawMoodSignal => {
    const coords = EMOTION_COORDINATES[detectedEmotion] || EMOTION_COORDINATES[EmotionLabel.NEUTRAL];
    const confidenceBoost = personalProfile ? 1.25 : 1.0;
    return {
      type: SignalType.FACE_EXPRESSION,
      energy: coords.energy,
      valence: coords.valence,
      arousal: coords.arousal,
      confidence: Math.min(0.99, detectedConfidence * confidenceBoost),
      isAvailable: true,
      detectedEmotion
    };
  }, [detectedEmotion, detectedConfidence, personalProfile]);

  // Clean up stream on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return {
    hasCameraPermission,
    isStreaming,
    videoRef,
    detectedEmotion,
    detectedConfidence,
    personalProfile,
    isCalibrating,
    calibrationStep,
    requestCamera,
    stopCamera,
    startCalibration,
    advanceCalibration,
    cancelCalibration,
    simulateEmotion,
    getFaceSignal
  };
}
