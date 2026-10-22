import React, { useEffect } from 'react';
import { JourneyTrack } from '../../types/track';
import { TargetMood } from '../../types/mood';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronDown,
  Gauge,
  Sliders,
  ExternalLink,
  Disc3,
  Layers,
  Sparkles
} from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface FullPlayerModalProps {
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
  useEffect(() => {
    triggerHaptic('light');
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  if (!currentTrack) return null;

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const handleProgressBarClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    triggerHaptic('light');
    onSeek(ratio);
  };

  const tempoShift = Math.round((effectiveTempo - 1.0) * 100);
  const tempoLabel = tempoShift > 0 ? `+${tempoShift}%` : tempoShift < 0 ? `${tempoShift}%` : 'Normal';

  return (
    <div className="fixed inset-0 z-50 bg-[#0A0E1A] overflow-y-auto flex flex-col justify-between pt-[max(env(safe-area-inset-top,0px),16px)] pb-[max(env(safe-area-inset-bottom,0px),24px)] px-6 select-none animate-in slide-in-from-bottom duration-300">
      {/* Background Ambient Aura */}
      <div
        className="fixed -top-40 inset-x-0 h-96 rounded-full blur-[140px] opacity-25 pointer-events-none"
        style={{ backgroundColor: targetMood.colorAccent }}
      />

      {/* Top Navigation Bar */}
      <div className="relative z-10 flex items-center justify-between py-2">
        <button
          onClick={() => {
            triggerHaptic('light');
            onClose();
          }}
          aria-label="Minimize full player"
          className="w-10 h-10 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center transition-colors active:scale-95"
        >
          <ChevronDown className="w-6 h-6" />
        </button>

        <div className="flex flex-col items-center">
          <span className="text-[10px] font-mono font-bold tracking-widest uppercase text-cyan-400">
            PHASE {phaseNumber} OF {totalPhases}
          </span>
          <span className="text-xs font-semibold text-slate-300 mt-0.5">
            Target: {targetMood.name}
          </span>
        </div>

        <button
          onClick={() => {
            triggerHaptic('light');
            onSpotifyClick();
          }}
          aria-label="Listen on Spotify"
          className="w-10 h-10 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-emerald-400 flex items-center justify-center transition-colors active:scale-95"
          title="Open Spotify"
        >
          <ExternalLink className="w-5 h-5" />
        </button>
      </div>

      {/* Center Artwork / Vinyl Canvas */}
      <div className="relative z-10 my-auto py-6 flex flex-col items-center justify-center">
        <div className="relative w-64 h-64 sm:w-72 sm:h-72 rounded-3xl overflow-hidden shadow-2xl border border-white/10 p-2 bg-slate-900/90">
          {/* Subtle Ambient Radial Glow */}
          <div
            className="absolute inset-0 rounded-3xl opacity-30 blur-xl pointer-events-none"
            style={{ backgroundColor: targetMood.colorAccent }}
          />

          {/* Vinyl Image */}
          <div className="relative w-full h-full rounded-2xl overflow-hidden bg-slate-950 flex items-center justify-center">
            {currentTrack.track.artworkUrl ? (
              <img
                src={currentTrack.track.artworkUrl}
                alt={currentTrack.track.title}
                className={`w-full h-full object-cover transition-transform duration-700 ${
                  isPlaying ? 'scale-105' : 'scale-100'
                }`}
              />
            ) : (
              <Disc3 className="w-24 h-24 text-cyan-500 animate-spin-slow" />
            )}

            {/* Invariant Pitch Lock Pill Overlay */}
            <div className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded-full bg-black/75 backdrop-blur-md border border-emerald-500/40 text-[9px] font-mono text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Pitch Lock 1.00x
            </div>
          </div>
        </div>

        {/* Track Title & Artist */}
        <div className="text-center mt-6 max-w-sm px-4">
          <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight leading-tight line-clamp-1 m-0">
            {currentTrack.track.title}
          </h2>
          <p className="text-sm font-medium text-slate-400 mt-1 line-clamp-1 m-0">
            {currentTrack.track.artist}
          </p>

          {/* Harmonic & Tempo Badges */}
          <div className="flex items-center justify-center gap-2 mt-3">
            <span className="text-[10px] font-mono font-bold px-2.5 py-1 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-500/30">
              Key: {currentTrack.track.camelotCode || '8B'} · {currentTrack.track.musicalMode === 1 ? 'Major' : 'Minor'}
            </span>
            <span
              onClick={onOpenTempoFineTune}
              className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded-full border cursor-pointer active:scale-95 transition-transform ${
                isTempoTuned
                  ? 'bg-amber-950/50 text-amber-300 border-amber-500/40'
                  : 'bg-slate-800 text-slate-300 border-slate-700'
              }`}
            >
              Speed: {effectiveTempo.toFixed(2)}x ({tempoLabel})
            </span>
          </div>
        </div>
      </div>

      {/* Bottom Controls Section */}
      <div className="relative z-10 w-full max-w-md mx-auto space-y-4">
        {/* Scrubber Progress Bar */}
        <div className="space-y-1.5">
          <div
            onClick={handleProgressBarClick}
            className="w-full h-3 bg-slate-800/80 rounded-full cursor-pointer relative overflow-hidden group py-1"
          >
            <div
              className="h-1.5 rounded-full bg-gradient-to-r from-cyan-400 to-blue-500 relative transition-all duration-150"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-white rounded-full shadow-md scale-0 group-hover:scale-100 transition-transform" />
            </div>
          </div>
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-0.5">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Transport Controls */}
        <div className="flex items-center justify-center gap-6 py-2">
          {/* Previous */}
          <button
            onClick={() => {
              triggerHaptic('light');
              onPrevious();
            }}
            className="w-12 h-12 rounded-full bg-slate-800/70 hover:bg-slate-750 text-slate-300 hover:text-white flex items-center justify-center transition-all active:scale-90"
            title="Previous Track"
          >
            <SkipBack className="w-5 h-5 fill-current" />
          </button>

          {/* Main Play/Pause Button */}
          <button
            onClick={() => {
              triggerHaptic('medium');
              onTogglePlay();
            }}
            className="w-16 h-16 rounded-full bg-cyan-400 hover:bg-cyan-300 text-slate-950 flex items-center justify-center shadow-xl shadow-cyan-400/30 transition-transform active:scale-90"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="w-7 h-7 fill-current" />
            ) : (
              <Play className="w-7 h-7 fill-current ml-1" />
            )}
          </button>

          {/* Next */}
          <button
            onClick={() => {
              triggerHaptic('light');
              onNext();
            }}
            className="w-12 h-12 rounded-full bg-slate-800/70 hover:bg-slate-750 text-slate-300 hover:text-white flex items-center justify-center transition-all active:scale-90"
            title="Next Track"
          >
            <SkipForward className="w-5 h-5 fill-current" />
          </button>
        </div>

        {/* Fine-Tune Bar Trigger Button */}
        <div className="flex justify-center pb-1">
          <button
            onClick={() => {
              triggerHaptic('light');
              onOpenTempoFineTune();
            }}
            className="text-xs text-slate-400 hover:text-cyan-300 flex items-center gap-1.5 py-1 px-3 rounded-full hover:bg-slate-800/50 transition-colors"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Fine-Tune Tempo Multiplier (0.96x–1.04x)</span>
          </button>
        </div>
      </div>
    </div>
  );
};
