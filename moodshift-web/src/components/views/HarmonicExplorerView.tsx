import React, { useState } from 'react';
import { MOCK_TRACKS } from '../../data/mockTracks';
import { camelotEngine } from '../../domain/CamelotHarmonicEngine';
import { Track } from '../../types/track';
import { Disc3, Sparkles, Music, ChevronRight, Check } from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface HarmonicExplorerViewProps {
  currentTrack?: Track | null;
  onSelectTrack: (track: Track) => void;
}

const getTrackCamelot = (t: Track): string => {
  return t.camelotCode || camelotEngine.toCamelot(t.musicalKey, t.musicalMode) || '8B';
};

const getCompatiblePositions = (code: string): string[] => {
  const parsed = camelotEngine.parseCamelot(code);
  if (!parsed) return [code];
  const { num, letter } = parsed;
  const oppLetter = letter === 'B' ? 'A' : 'B';
  const nextNum = (num % 12) + 1;
  const prevNum = (num - 2 + 12) % 12 + 1;
  return [
    code,
    `${nextNum}${letter}`,
    `${prevNum}${letter}`,
    `${num}${oppLetter}`
  ];
};

export const HarmonicExplorerView: React.FC<HarmonicExplorerViewProps> = ({
  currentTrack,
  onSelectTrack
}) => {
  const [selectedCamelot, setSelectedCamelot] = useState<string>(
    currentTrack ? getTrackCamelot(currentTrack) : '8B'
  );
  const [modeFilter, setModeFilter] = useState<'ALL' | 'MAJOR' | 'MINOR'>('ALL');

  // Camelot positions
  const camelotKeys = [
    { pos: '1B', name: 'B Maj', mode: 1 },
    { pos: '2B', name: 'F# Maj', mode: 1 },
    { pos: '3B', name: 'Db Maj', mode: 1 },
    { pos: '4B', name: 'Ab Maj', mode: 1 },
    { pos: '5B', name: 'Eb Maj', mode: 1 },
    { pos: '6B', name: 'Bb Maj', mode: 1 },
    { pos: '7B', name: 'F Maj', mode: 1 },
    { pos: '8B', name: 'C Maj', mode: 1 },
    { pos: '9B', name: 'G Maj', mode: 1 },
    { pos: '10B', name: 'D Maj', mode: 1 },
    { pos: '11B', name: 'A Maj', mode: 1 },
    { pos: '12B', name: 'E Maj', mode: 1 },
    { pos: '8A', name: 'A Min', mode: 0 },
    { pos: '9A', name: 'E Min', mode: 0 },
    { pos: '10A', name: 'B Min', mode: 0 },
    { pos: '11A', name: 'F# Min', mode: 0 },
    { pos: '12A', name: 'C# Min', mode: 0 },
    { pos: '1A', name: 'Ab Min', mode: 0 }
  ];

  // Compatible keys calculation
  const compatiblePositions = getCompatiblePositions(selectedCamelot);

  // Filtered tracks
  const filteredTracks = MOCK_TRACKS.filter((t) => {
    const pos = getTrackCamelot(t);
    const matchesKey = pos === selectedCamelot || compatiblePositions.includes(pos);
    if (!matchesKey) return false;
    if (modeFilter === 'MAJOR') return t.musicalMode === 1;
    if (modeFilter === 'MINOR') return t.musicalMode === 0;
    return true;
  });

  return (
    <div className="space-y-5 pb-36 animate-in fade-in duration-300">
      {/* Title & Harmonic Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-950/80 via-slate-900/90 to-[#0E1526] p-5 border border-white/10 shadow-xl">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-8 h-8 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center border border-cyan-500/30">
            <Disc3 className="w-4 h-4 animate-spin-slow" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight m-0">Camelot Harmonic Wheel</h2>
            <p className="text-[11px] text-slate-400 m-0">Zero-distortion key matching & energy modulation</p>
          </div>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed mt-2">
          Tracks composed in adjacent keys or relative majors/minors transition seamlessly without dissonant clashes.
        </p>

        {/* Selected Key Status Pill */}
        <div className="mt-3 flex items-center justify-between p-3 rounded-2xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Selected Root:</span>
            <span className="text-sm font-bold font-mono text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded-lg border border-cyan-800/40">
              {selectedCamelot}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-slate-300 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
            Compatible: {compatiblePositions.join(', ')}
          </div>
        </div>
      </div>

      {/* Tonality Mode Filter Buttons */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400 font-medium shrink-0">Filter Mode:</span>
        <div className="flex items-center gap-1.5 flex-1">
          {(['ALL', 'MAJOR', 'MINOR'] as const).map((m) => (
            <button
              key={m}
              onClick={() => {
                triggerHaptic('light');
                setModeFilter(m);
              }}
              className={`flex-1 py-1.5 px-2 rounded-xl text-xs font-bold transition-all active:scale-95 ${
                modeFilter === m
                  ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'bg-slate-900/80 text-slate-400 border border-slate-800 hover:text-white'
              }`}
            >
              {m === 'ALL' ? 'All Keys' : m === 'MAJOR' ? '✨ Major (Joy)' : '🌙 Minor (Deep)'}
            </button>
          ))}
        </div>
      </div>

      {/* Quick Camelot Key Chips Carousel */}
      <div>
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 px-1">
          Explore Camelot Positions
        </h3>
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none">
          {camelotKeys
            .filter((k) => (modeFilter === 'MAJOR' ? k.mode === 1 : modeFilter === 'MINOR' ? k.mode === 0 : true))
            .map((k) => {
              const isSelected = selectedCamelot === k.pos;
              const isComp = compatiblePositions.includes(k.pos);

              return (
                <button
                  key={k.pos}
                  onClick={() => {
                    triggerHaptic('light');
                    setSelectedCamelot(k.pos);
                  }}
                  className={`flex flex-col items-center justify-center min-w-[70px] py-2 px-2.5 rounded-2xl border transition-all shrink-0 active:scale-95 ${
                    isSelected
                      ? 'bg-cyan-500 text-slate-950 font-bold border-cyan-400 shadow-lg shadow-cyan-500/25'
                      : isComp
                      ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40 hover:bg-emerald-900/50'
                      : 'bg-slate-900/80 text-slate-300 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <span className="text-xs font-mono font-bold leading-tight">{k.pos}</span>
                  <span className={`text-[10px] mt-0.5 leading-none ${isSelected ? 'text-slate-900 font-semibold' : 'text-slate-400'}`}>
                    {k.name}
                  </span>
                </button>
              );
            })}
        </div>
      </div>

      {/* Compatible Tracks in This Key */}
      <div>
        <div className="flex items-center justify-between px-1 mb-2">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Harmonically Matched Tracks ({filteredTracks.length})
          </h3>
          <span className="text-[11px] text-cyan-400 font-medium">1-Tap to Play</span>
        </div>

        <div className="space-y-2">
          {filteredTracks.map((track) => {
            const pos = getTrackCamelot(track);
            const isExact = pos === selectedCamelot;

            return (
              <div
                key={track.id}
                onClick={() => {
                  triggerHaptic('medium');
                  onSelectTrack(track);
                }}
                className="group flex items-center justify-between p-3 rounded-2xl bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800/80 hover:border-cyan-500/30 transition-all cursor-pointer active:scale-[0.98]"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-slate-800 shrink-0 overflow-hidden border border-white/5 relative">
                    {track.artworkUrl ? (
                      <img src={track.artworkUrl} alt={track.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-cyan-950/60">
                        <Music className="w-4 h-4 text-cyan-400" />
                      </div>
                    )}
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-bold text-white truncate leading-tight group-hover:text-cyan-300 transition-colors">
                      {track.title}
                    </h4>
                    <p className="text-[11px] text-slate-400 truncate mt-0.5">{track.artist}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-lg border font-bold ${
                      isExact
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                        : 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30'
                    }`}
                  >
                    {pos} · {track.musicalMode === 1 ? 'Maj' : 'Min'}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">{track.tempoBpm || 105} BPM</span>
                  <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 transition-colors" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
