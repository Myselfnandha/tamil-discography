import React from 'react';
import { JourneyTrack } from '../../types/track';
import { TargetMood } from '../../types/mood';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronDown,
  Gauge,
  Sliders,
  Music2,
  Sparkles,
  ExternalLink,
  Disc3,
  Layers
} from 'lucide-react';

interface FullPlayerModalProps {
  currentTrack: JourneyTrack | null;
  phaseNumber: number;
  totalPhases: number;
  isPlaying: boolean;
  progress: number;
  currentTime: number;
  duration: number;
  effectiveTempo: number;
  isTempoTuned: boolean;
  targetMood: TargetMood;
  onTogglePlay: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onSeek: (ratio: number) => void;
  onClose: () => void;
  onOpenTempoFineTune: () => void;
  onSpotifyClick: () => void;
}

export const FullPlayerModal: React.FC<FullPlayerModalProps> = ({
  currentTrack,
  phaseNumber,
  totalPhases,
  isPlaying,
  progress,
  currentTime,
  duration,
  effectiveTempo,
  isTempoTuned,
  targetMood,
  onTogglePlay,
  onNext,
  onPrevious,
  onSeek,
  onClose,
  onOpenTempoFineTune,
  onSpotifyClick
}) => {
  if (!currentTrack) return null;

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const handleProgressBarClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    onSeek(ratio);
  };

  const tempoShift = Math.round((effectiveTempo - 1.0) * 100);
  const tempoLabel = tempoShift > 0 ? `+${tempoShift}%` : tempoShift < 0 ? `${tempoShift}%` : 'Normal';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-2xl animate-fadeIn">
      <div className="w-full max-w-xl flex flex-col gap-6">
        {/* Top bar */}
        <div className="flex items-center justify-between">
          <button
            onClick={onClose}
            aria-label="Minimize full player"
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <ChevronDown className="w-6 h-6" />
          </button>

          <div className="flex flex-col items-center">
            <span className="text-[11px] font-bold tracking-widest uppercase text-cyan-400">
              MoodShift Journey • Phase {phaseNumber} of {totalPhases}
            </span>
            <span className="text-xs text-slate-400">
              Target: {targetMood.name}
            </span>
          </div>

          <button
            onClick={onSpotifyClick}
            aria-label="Listen on Spotify"
            className="p-2 rounded-xl text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
            title="Open Spotify"
          >
            <ExternalLink className="w-5 h-5" />
          </button>
        </div>

        {/* Vinyl / Cover Art Canvas */}
        <div className="relative aspect-square max-w-sm mx-auto w-full flex items-center justify-center">
          {/* Outer glow based on target mood accent */}
          <div
            className="absolute inset-4 rounded-full blur-3xl opacity-30 transition-all duration-700"
            style={{
              backgroundColor: targetMood.colorAccent
            }}
          />

          {/* Vinyl Disc Container */}
          <div className="relative w-64 h-64 sm:w-72 sm:h-72 rounded-full p-2 bg-gradient-to-tr from-slate-900 to-black border-4 border-slate-800 shadow-2xl flex items-center justify-center">
            {/* Spinning Groove animation */}
            <div
              className={`w-full h-full rounded-full border border-white/5 flex items-center justify-center transition-all ${
                isPlaying ? 'animate-spin-slow' : ''
              }`}
            >
              {/* Center Artwork */}
              <div className="relative w-36 h-36 sm:w-40 sm:h-40 rounded-full overflow-hidden border-4 border-slate-950 shadow-inner">
                {currentTrack.track.artworkUrl ? (
                  <img
                    src={currentTrack.track.artworkUrl}
                    alt={currentTrack.track.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full bg-slate-800 flex items-center justify-center text-slate-500">
                    <Disc3 className="w-16 h-16" />
                  </div>
                )}
                {/* Spindle hole */}
                <div className="absolute inset-0 m-auto w-6 h-6 rounded-full bg-slate-950 border-2 border-slate-700 shadow-inner" />
              </div>
            </div>
          </div>
        </div>

        {/* Track Title & Artist */}
        <div className="text-center space-y-1">
          <h2 className="text-2xl font-bold text-white tracking-tight">
            {currentTrack.track.title}
          </h2>
          <p className="text-sm text-slate-400">
            {currentTrack.track.artist}
          </p>
        </div>

        {/* Harmonic Camelot & Pitch Invariant Pill */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          {currentTrack.track.camelotCode && (
            <Badge variant="purple" size="md">
              Camelot {currentTrack.track.camelotCode}
            </Badge>
          )}

          {currentTrack.track.tempoBpm && (
            <Badge variant="neutral" size="md">
              {Math.round(currentTrack.track.tempoBpm)} BPM
            </Badge>
          )}

          <Badge variant={tempoShift > 0 ? 'emerald' : tempoShift < 0 ? 'amber' : 'neutral'} size="md">
            Tempo: {tempoLabel} ({effectiveTempo.toFixed(2)}x)
          </Badge>

          <span className="text-[11px] text-slate-500 font-mono">
            Pitch locked: 1.0x
          </span>
        </div>

        {/* Track transition rationale */}
        <div className="p-3 rounded-xl bg-white/[0.04] border border-white/5 text-center text-xs text-slate-300">
          <span className="text-cyan-400 font-medium">Harmonic Flow: </span>
          {currentTrack.reason}
        </div>

        {/* Scrubber */}
        <div className="space-y-1.5">
          <div
            onClick={handleProgressBarClick}
            className="w-full h-2 rounded-full bg-white/10 hover:h-2.5 transition-all cursor-pointer relative overflow-hidden"
          >
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 rounded-full"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Playback Controls */}
        <div className="flex items-center justify-between px-6">
          <button
            onClick={onOpenTempoFineTune}
            className="p-3 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-white/5 transition-colors"
            title="Adjust Tempo Multiplier"
          >
            <Sliders className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-5">
            <button
              onClick={onPrevious}
              aria-label="Previous track"
              className="p-3 text-slate-300 hover:text-white hover:scale-110 active:scale-95 transition-all"
            >
              <SkipBack className="w-7 h-7" />
            </button>

            <button
              onClick={onTogglePlay}
              aria-label={isPlaying ? 'Pause' : 'Play'}
              className="w-16 h-16 rounded-full bg-gradient-to-tr from-cyan-400 to-emerald-400 text-slate-950 flex items-center justify-center shadow-xl hover:scale-105 active:scale-95 transition-all"
            >
              {isPlaying ? (
                <Pause className="w-8 h-8 fill-current" />
              ) : (
                <Play className="w-8 h-8 fill-current ml-1" />
              )}
            </button>

            <button
              onClick={onNext}
              aria-label="Next track"
              className="p-3 text-slate-300 hover:text-white hover:scale-110 active:scale-95 transition-all"
            >
              <SkipForward className="w-7 h-7" />
            </button>
          </div>

          <button
            onClick={onClose}
            className="p-3 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            title="Minimize"
          >
            <Layers className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};
