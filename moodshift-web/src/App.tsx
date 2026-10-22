import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { FlowMode, MoodSnapshot, TargetMood, EmotionLabel, ScanSource } from './types/mood';
import { MoodJourney } from './types/journey';
import { Track } from './types/track';
import { useAutoSense } from './hooks/useAutoSense';
import { useCameraSensor } from './hooks/useCameraSensor';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { smartPredictor } from './domain/SmartTargetPredictor';
import { journeyPlanner } from './domain/JourneyPlanner';
import { MOCK_TRACKS } from './data/mockTracks';
import { DEFAULT_TARGET_MOODS } from './data/defaultTargetMoods';

// Components
import { TopHeader } from './components/dashboard/TopHeader';
import { FixMyMoodCard } from './components/dashboard/FixMyMoodCard';
import { RecentJourneys } from './components/dashboard/RecentJourneys';
import { PlaylistCarousel } from './components/dashboard/PlaylistCarousel';
import { FaceCalibrationModal } from './components/scan/FaceCalibrationModal';
import { CameraScanOverlay } from './components/scan/CameraScanOverlay';
import { SelfReportWheel } from './components/scan/SelfReportWheel';
import { TargetPickerModal } from './components/journey/TargetPickerModal';
import { JourneyPreviewSheet } from './components/journey/JourneyPreviewSheet';
import { NowPlayingBar } from './components/player/NowPlayingBar';
import { FullPlayerModal } from './components/player/FullPlayerModal';
import { TempoFineTuneSheet } from './components/player/TempoFineTuneSheet';
import { SpotifyFallbackAlert } from './components/player/SpotifyFallbackAlert';

export default function App() {
  // 1. Flow Mode
  const [flowMode, setFlowMode] = useState<FlowMode>(FlowMode.GUIDED);

  // 2. Auto-Sensing & Mood State
  const { currentMood: sensedMood, isScanning: isAutoSensing, refreshScan } = useAutoSense();
  const [customMood, setCustomMood] = useState<MoodSnapshot | null>(null);
  const activeMood = customMood || sensedMood;

  // 3. Target Mood State
  const [selectedTarget, setSelectedTarget] = useState<TargetMood | null>(null);
  const recommendedTarget = useMemo(() => {
    return selectedTarget || smartPredictor.predictTargetMood(activeMood);
  }, [selectedTarget, activeMood]);

  // 4. Audio Engine Hook
  const audioPlayer = useAudioPlayer(recommendedTarget);

  // 5. Camera & Face Calibration Hook
  const cameraSensor = useCameraSensor();

  // 6. Active Journey State
  const [currentJourney, setCurrentJourney] = useState<MoodJourney | null>(null);

  // 7. Modals & Overlays State
  const [isCalibrationOpen, setIsCalibrationOpen] = useState(false);
  const [isManualScanOpen, setIsManualScanOpen] = useState(false);
  const [isSelfReportOpen, setIsSelfReportOpen] = useState(false);
  const [isTargetPickerOpen, setIsTargetPickerOpen] = useState(false);
  const [isJourneyPreviewOpen, setIsJourneyPreviewOpen] = useState(false);
  const [isFullPlayerOpen, setIsFullPlayerOpen] = useState(false);
  const [isTempoFineTuneOpen, setIsTempoFineTuneOpen] = useState(false);
  const [spotifyAlertTrack, setSpotifyAlertTrack] = useState<Track | null>(null);

  // Auto-generate journey on target change or mood change if no active playback
  const generateNewJourney = useCallback((target: TargetMood): MoodJourney => {
    const journey = journeyPlanner.planJourney(activeMood, target, MOCK_TRACKS);
    setCurrentJourney(journey);
    return journey;
  }, [activeMood]);

  // Handler: Start journey
  const handleStartJourney = (target?: TargetMood) => {
    const t = target || recommendedTarget;
    const journey = generateNewJourney(t);
    audioPlayer.startJourney(journey);
  };

  // Handler: Preview journey first
  const handlePreviewJourney = (target?: TargetMood) => {
    const t = target || recommendedTarget;
    generateNewJourney(t);
    setIsJourneyPreviewOpen(true);
  };

  // Handler: Self-report confirm
  const handleSelfReportConfirm = (energy: number, valence: number) => {
    const updated: MoodSnapshot = {
      ...activeMood,
      id: `sr-${Date.now()}`,
      energy,
      valence,
      dominantEmotion: energy > 0.6 ? EmotionLabel.HAPPY : energy < 0.3 ? EmotionLabel.SAD : EmotionLabel.NEUTRAL,
      confidence: 0.95,
      timestamp: new Date().toISOString(),
      source: ScanSource.MANUAL
    };
    setCustomMood(updated);
    setIsSelfReportOpen(false);
  };

  // Handler: Camera detected emotion confirm
  const handleCameraEmotionApply = (emotion: EmotionLabel) => {
    let energy = 0.5;
    let valence = 0.5;
    switch (emotion) {
      case EmotionLabel.HAPPY:
        energy = 0.75;
        valence = 0.85;
        break;
      case EmotionLabel.SAD:
        energy = 0.25;
        valence = 0.25;
        break;
      case EmotionLabel.ANGRY:
        energy = 0.8;
        valence = 0.2;
        break;
      case EmotionLabel.SURPRISED:
        energy = 0.85;
        valence = 0.7;
        break;
      default:
        energy = 0.5;
        valence = 0.5;
        break;
    }
    const updated: MoodSnapshot = {
      ...activeMood,
      id: `cam-${Date.now()}`,
      energy,
      valence,
      dominantEmotion: emotion,
      confidence: 0.88,
      timestamp: new Date().toISOString(),
      source: ScanSource.MANUAL
    };
    setCustomMood(updated);
    setIsManualScanOpen(false);
  };

  // Playlist tag quick select
  const handleSelectMoodTag = (tag: string) => {
    const matched = DEFAULT_TARGET_MOODS.find(m => m.name.toLowerCase() === tag.toLowerCase());
    if (matched) {
      setSelectedTarget(matched);
      handlePreviewJourney(matched);
    }
  };

  // Spotify deeplink handler (triggers DSP notice modal)
  const handleSpotifyPrompt = () => {
    if (audioPlayer.currentTrack) {
      setSpotifyAlertTrack(audioPlayer.currentTrack.track);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Background ambient gradient orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div
          className="absolute -top-32 -left-32 w-96 h-96 rounded-full blur-[140px] opacity-20 transition-all duration-1000"
          style={{ backgroundColor: recommendedTarget.colorAccent }}
        />
        <div className="absolute top-1/3 -right-32 w-[30rem] h-[30rem] rounded-full blur-[160px] opacity-15 bg-blue-600/30" />
        <div className="absolute -bottom-32 left-1/4 w-[28rem] h-[28rem] rounded-full blur-[150px] opacity-10 bg-indigo-600/20" />
      </div>

      {/* Main Container */}
      <div className="relative z-10 flex-1 flex flex-col max-w-6xl w-full mx-auto px-4 sm:px-6 pt-3 pb-28">
        {/* Top Header */}
        <TopHeader
          flowMode={flowMode}
          onFlowModeChange={setFlowMode}
          personalProfile={cameraSensor.personalProfile}
          onOpenCalibration={() => setIsCalibrationOpen(true)}
          onOpenManualScan={() => setIsManualScanOpen(true)}
        />

        {/* Dashboard Content */}
        <main className="flex-1 flex flex-col gap-6 mt-4">
          {/* Primary Hero: Fix My Mood Card */}
          <FixMyMoodCard
            currentMood={activeMood}
            recommendedTarget={recommendedTarget}
            isAutoSensing={isAutoSensing}
            onStartJourney={() => handleStartJourney(recommendedTarget)}
            onChangeTarget={() => setIsTargetPickerOpen(true)}
            onOpenCorrection={() => setIsSelfReportOpen(true)}
            onRefreshSense={refreshScan}
          />

          {/* Connected Playlists */}
          <PlaylistCarousel onSelectMoodTag={handleSelectMoodTag} />

          {/* Recent MoodShift Journeys */}
          <RecentJourneys />
        </main>
      </div>

      {/* Sticky Bottom Now Playing Bar */}
      {audioPlayer.currentTrack && (
        <NowPlayingBar
          currentTrack={audioPlayer.currentTrack}
          phaseNumber={audioPlayer.currentPhaseNumber}
          isPlaying={audioPlayer.isPlaying}
          progress={audioPlayer.progress}
          currentTime={audioPlayer.currentTime}
          duration={audioPlayer.duration}
          effectiveTempo={audioPlayer.effectiveTempo}
          isTempoTuned={audioPlayer.isTempoTuned}
          isCrossfading={audioPlayer.isCrossfading}
          onTogglePlay={audioPlayer.togglePlay}
          onNext={audioPlayer.nextTrack}
          onPrevious={audioPlayer.previousTrack}
          onSeek={audioPlayer.seek}
          onOpenFullPlayer={() => setIsFullPlayerOpen(true)}
          onOpenTempoFineTune={() => setIsTempoFineTuneOpen(true)}
          onSpotifyClick={handleSpotifyPrompt}
        />
      )}

      {/* Modal: Face Calibration */}
      <FaceCalibrationModal
        isOpen={isCalibrationOpen}
        step={cameraSensor.calibrationStep}
        onAdvance={cameraSensor.advanceCalibration}
        onCancel={() => setIsCalibrationOpen(false)}
        videoRef={cameraSensor.videoRef}
        isStreaming={cameraSensor.isStreaming}
        onRequestCamera={cameraSensor.requestCamera}
      />

      {/* Modal: Camera Scan Overlay */}
      <CameraScanOverlay
        isOpen={isManualScanOpen}
        onClose={() => setIsManualScanOpen(false)}
        onApplyEmotion={handleCameraEmotionApply}
        detectedEmotion={cameraSensor.detectedEmotion}
        detectedConfidence={cameraSensor.detectedConfidence}
        isStreaming={cameraSensor.isStreaming}
        videoRef={cameraSensor.videoRef}
        onRequestCamera={cameraSensor.requestCamera}
      />

      {/* Modal: Self-Report Mood Wheel */}
      {isSelfReportOpen && (
        <SelfReportWheel
          initialEnergy={activeMood.energy}
          initialValence={activeMood.valence}
          onConfirm={handleSelfReportConfirm}
          onCancel={() => setIsSelfReportOpen(false)}
        />
      )}

      {/* Modal: Target Mood Picker */}
      {isTargetPickerOpen && (
        <TargetPickerModal
          selectedMoodId={recommendedTarget.id}
          onSelectMood={(mood) => {
            setSelectedTarget(mood);
            setIsTargetPickerOpen(false);
          }}
          onClose={() => setIsTargetPickerOpen(false)}
        />
      )}

      {/* Modal: 3-Phase Journey Preview Sheet */}
      {isJourneyPreviewOpen && currentJourney && (
        <JourneyPreviewSheet
          journey={currentJourney}
          onStartJourney={() => {
            audioPlayer.startJourney(currentJourney);
            setIsJourneyPreviewOpen(false);
          }}
          onRegenerate={() => generateNewJourney(recommendedTarget)}
          onClose={() => setIsJourneyPreviewOpen(false)}
        />
      )}

      {/* Modal: Full Immersive Player */}
      {isFullPlayerOpen && audioPlayer.currentTrack && (
        <FullPlayerModal
          currentTrack={audioPlayer.currentTrack}
          phaseNumber={audioPlayer.currentPhaseNumber}
          totalPhases={audioPlayer.journey?.phases.length || 3}
          isPlaying={audioPlayer.isPlaying}
          progress={audioPlayer.progress}
          currentTime={audioPlayer.currentTime}
          duration={audioPlayer.duration}
          effectiveTempo={audioPlayer.effectiveTempo}
          isTempoTuned={audioPlayer.isTempoTuned}
          targetMood={recommendedTarget}
          onTogglePlay={audioPlayer.togglePlay}
          onNext={audioPlayer.nextTrack}
          onPrevious={audioPlayer.previousTrack}
          onSeek={audioPlayer.seek}
          onClose={() => setIsFullPlayerOpen(false)}
          onOpenTempoFineTune={() => setIsTempoFineTuneOpen(true)}
          onSpotifyClick={handleSpotifyPrompt}
        />
      )}

      {/* Modal: Tempo Fine Tune Sheet */}
      {isTempoFineTuneOpen && (
        <TempoFineTuneSheet
          currentTrack={audioPlayer.currentTrack}
          targetMood={recommendedTarget}
          effectiveTempo={audioPlayer.effectiveTempo}
          manualTempo={audioPlayer.manualTempo}
          isTempoTuned={audioPlayer.isTempoTuned}
          onSetManualTempo={audioPlayer.setManualTempo}
          onToggleTempoTuned={audioPlayer.toggleTempoTuning}
          onClose={() => setIsTempoFineTuneOpen(false)}
        />
      )}

      {/* Modal: Spotify Fallback Alert */}
      {spotifyAlertTrack && (
        <SpotifyFallbackAlert
          track={spotifyAlertTrack}
          onConfirmOpenSpotify={() => {
            if (spotifyAlertTrack.spotifyUri) {
              window.open(spotifyAlertTrack.spotifyUri, '_blank');
            }
            setSpotifyAlertTrack(null);
          }}
          onStayInApp={() => setSpotifyAlertTrack(null)}
          onClose={() => setSpotifyAlertTrack(null)}
        />
      )}
    </div>
  );
}
