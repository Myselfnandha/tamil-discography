import React from 'react';
import { JourneyTrack } from '../../types/track';
import { Badge } from '../common/Badge';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Maximize2,
  Gauge,
  Sliders,
  Sparkles,
  ExternalLink,
  Disc3
} from 'lucide-react';

interface NowPlayingBarProps {
  currentTrack: JourneyTrack | null;
  phaseNumber: number;
  isPlaying: boolean;
  progress: number;
  currentTime: number;
  duration: number;
  effectiveTempo: number;
  isTempoTuned: boolean;
  isCrossfading: boolean;
  onTogglePlay: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onSeek: (ratio: number) => void;
  onOpenFullPlayer: () => void;
  onOpenTempoFineTune: () => void;
  onSpotifyClick: () => void;
}

export const NowPlayingBar: React.FC<NowPlayingBarProps> = ({
  currentTrack,
  phaseNumber,
  isPlaying,
  progress,
  currentTime,
  duration,
  effectiveTempo,
  isTempoTuned,
  isCrossfading,
  onTogglePlay,
  onNext,
  onPrevious,
  onSeek,
  onOpenFullPlayer,
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
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-slate-950/90 backdrop-blur-xl border-t border-white/10 shadow-[0_-10px_30px_rgba(0,0,0,0.5)]">
      {/* Progress scrubber bar across top edge */}
      <div
        onClick={handleProgressBarClick}
        className="w-full h-1 bg-white/10 hover:h-2 transition-all cursor-pointer group relative"
      >
        <div
          className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 group-hover:from-cyan-400 group-hover:to-emerald-300 transition-all duration-150"
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      <div className="max-w-7xl mx-auto px-4 py-2.5 flex items-center justify-between gap-4">
        {/* Left: Track Info & Artwork */}
        <div className="flex items-center gap-3 min-w-0 w-1/3">
          <div
            onClick={onOpenFullPlayer}
            className="relative cursor-pointer group shrink-0"
          >
            {currentTrack.track.artworkUrl ? (
              <img
                src={currentTrack.track.artworkUrl}
                alt={currentTrack.track.title}
                className="w-12 h-12 rounded-lg object-cover border border-white/10 group-hover:opacity-80 transition-opacity"
              />
            ) : (
              <div className="w-12 h-12 rounded-lg bg-slate-800 border border-white/10 flex items-center justify-center text-slate-400">
                <Disc3 className="w-6 h-6 animate-spin-slow" />
              </div>
            )}
            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40 rounded-lg">
              <Maximize2 className="w-4 h-4 text-white" />
            </div>
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold tracking-wider uppercase text-cyan-400">
                Phase {phaseNumber}
              </span>
              {isCrossfading && (
                <span className="text-[10px] text-amber-400 font-mono animate-pulse">
                  • Crossfading...
                </span>
              )}
            </div>
            <h4
              onClick={onOpenFullPlayer}
              className="text-sm font-semibold text-white truncate cursor-pointer hover:text-cyan-300 transition-colors"
            >
              {currentTrack.track.title}
            </h4>
            <p className="text-xs text-slate-400 truncate">
              {currentTrack.track.artist}
            </p>
          </div>
        </div>

        {/* Center: Playback Controls */}
        <div className="flex flex-col items-center gap-1 shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={onPrevious}
              aria-label="Previous track"
              className="p-2 text-slate-400 hover:text-white transition-colors"
            >
              <SkipBack className="w-5 h-5" />
            </button>

            <button
              onClick={onTogglePlay}
              aria-label={isPlaying ? 'Pause' : 'Play'}
              className="w-10 h-10 rounded-full bg-white text-slate-950 flex items-center justify-center shadow-lg hover:scale-105 active:scale-95 transition-all"
            >
              {isPlaying ? (
                <Pause className="w-5 h-5 fill-current" />
              ) : (
                <Play className="w-5 h-5 fill-current ml-0.5" />
              )}
            </button>

            <button
              onClick={onNext}
              aria-label="Next track"
              className="p-2 text-slate-400 hover:text-white transition-colors"
            >
              <SkipForward className="w-5 h-5" />
            </button>
          </div>

          <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
            <span>{formatTime(currentTime)}</span>
            <span>/</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Right: Mood Tempo Badge & Quick Actions */}
        <div className="flex items-center justify-end gap-2.5 w-1/3 shrink-0">
          {/* Camelot Key Pill */}
          {currentTrack.track.camelotCode && (
            <Badge variant="purple" size="sm" className="hidden sm:inline-flex">
              {currentTrack.track.camelotCode}
            </Badge>
          )}

          {/* Discreet Mood Tempo Badge (Clickable for fine-tune sheet) */}
          <button
            onClick={onOpenTempoFineTune}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border transition-all ${
              isTempoTuned
                ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30 hover:bg-cyan-500/20 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
                : 'bg-white/5 text-slate-400 border-white/10 hover:bg-white/10'
            }`}
            title="Fine-tune Dynamic Mood Tempo (Pitch Locked at 1.0x)"
          >
            <Gauge className="w-3.5 h-3.5 text-cyan-400" />
            <span>Mood Tempo: {effectiveTempo.toFixed(2)}x</span>
            <Sliders className="w-3 h-3 text-slate-400 ml-0.5" />
          </button>

          {/* External Spotify Fallback Link */}
          <button
            onClick={onSpotifyClick}
            aria-label="Listen on Spotify"
            className="p-2 rounded-lg text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors hidden md:flex items-center gap-1 text-xs"
            title="Open in Spotify (DSP disabled outside browser)"
          >
            <ExternalLink className="w-4 h-4" />
          </button>

          {/* Maximize to full player */}
          <button
            onClick={onOpenFullPlayer}
            aria-label="Maximize player"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
