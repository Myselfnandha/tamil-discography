import React from 'react';
import { JourneyTrack } from '../../types/track';
import { Play, Pause, SkipForward, Sliders, Music } from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface MobileFloatingPlayerProps {
  currentTrack: JourneyTrack;
  isPlaying: boolean;
  progress: number;
  effectiveTempo: number;
  isTempoTuned: boolean;
  onTogglePlay: () => void;
  onNext: () => void;
  onOpenFullPlayer: () => void;
  onOpenTempoFineTune: (e: React.MouseEvent) => void;
}

export const MobileFloatingPlayer: React.FC<MobileFloatingPlayerProps> = ({
  currentTrack,
  isPlaying,
  progress,
  effectiveTempo,
  isTempoTuned,
  onTogglePlay,
  onNext,
  onOpenFullPlayer,
  onOpenTempoFineTune
}) => {
  const { track } = currentTrack;

  return (
    <div
      className="fixed left-3 right-3 z-30 select-none transition-all duration-300"
      style={{
        bottom: 'calc(62px + max(env(safe-area-inset-bottom, 0px), 10px))'
      }}
    >
      <div
        onClick={() => {
          triggerHaptic('light');
          onOpenFullPlayer();
        }}
        className="max-w-md mx-auto relative overflow-hidden rounded-2xl bg-[#13192B]/95 backdrop-blur-2xl border border-white/10 shadow-2xl p-2.5 flex items-center justify-between gap-3 active:scale-[0.99] transition-transform cursor-pointer group"
      >
        {/* Top Progress Micro-Bar */}
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-slate-800">
          <div
            className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Left: Thumbnail & Spinning Vinyl indicator */}
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="relative w-11 h-11 rounded-xl overflow-hidden bg-slate-800 shrink-0 border border-white/10 shadow-md">
            {track.artworkUrl ? (
              <img
                src={track.artworkUrl}
                alt={track.title}
                className={`w-full h-full object-cover transition-transform ${
                  isPlaying ? 'scale-105' : 'grayscale-[20%]'
                }`}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-cyan-900 to-indigo-950">
                <Music className="w-5 h-5 text-cyan-400" />
              </div>
            )}
            {/* Spinning disc ring overlay */}
            {isPlaying && (
              <div className="absolute inset-0 rounded-xl border-2 border-cyan-400/40 animate-pulse pointer-events-none" />
            )}
          </div>

          {/* Track Metadata */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <h4 className="text-xs font-bold text-white truncate leading-tight m-0">{track.title}</h4>
              <span className="text-[9px] font-mono font-bold px-1 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/40 shrink-0">
                {currentTrack.track.camelotCode || '8B'}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-[11px] text-slate-400 truncate leading-tight m-0">{track.artist}</p>
              <span className="text-slate-600">·</span>
              <span
                className={`text-[10px] font-mono px-1 py-0.2 rounded shrink-0 font-medium ${
                  isTempoTuned ? 'text-amber-300 bg-amber-950/40' : 'text-slate-300 bg-slate-800/60'
                }`}
              >
                {effectiveTempo.toFixed(2)}x
              </span>
            </div>
          </div>
        </div>

        {/* Right: Touch Controls */}
        <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
          {/* Tempo DSP Tune Quick Button */}
          <button
            onClick={(e) => {
              triggerHaptic('light');
              onOpenTempoFineTune(e);
            }}
            className="w-8 h-8 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 flex items-center justify-center transition-colors active:scale-95"
            title="Fine-tune Tempo"
          >
            <Sliders className="w-3.5 h-3.5" />
          </button>

          {/* Play/Pause Button */}
          <button
            onClick={() => {
              triggerHaptic('medium');
              onTogglePlay();
            }}
            className="w-10 h-10 rounded-full bg-cyan-400 hover:bg-cyan-300 text-slate-950 flex items-center justify-center shadow-lg shadow-cyan-400/30 transition-transform active:scale-90"
          >
            {isPlaying ? (
              <Pause className="w-5 h-5 fill-current" />
            ) : (
              <Play className="w-5 h-5 fill-current ml-0.5" />
            )}
          </button>

          {/* Next Button */}
          <button
            onClick={() => {
              triggerHaptic('light');
              onNext();
            }}
            className="w-8 h-8 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center transition-colors active:scale-95"
            title="Next Track"
          >
            <SkipForward className="w-4 h-4 fill-current" />
          </button>
        </div>
      </div>
    </div>
  );
};
