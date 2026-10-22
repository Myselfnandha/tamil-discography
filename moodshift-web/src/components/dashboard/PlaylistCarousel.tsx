import React from 'react';
import { GlassCard } from '../common/GlassCard';
import { Library, Disc3, Sparkles } from 'lucide-react';

export interface PlaylistCarouselProps {
  onSelectMoodTag: (tag: string) => void;
}

export const PlaylistCarousel: React.FC<PlaylistCarouselProps> = ({ onSelectMoodTag }) => {
  const playlists = [
    { id: 'p1', title: 'Late Night Tamil Lofi', artist: 'Santhosh & Sean Roldan', tracks: 24, bg: 'from-indigo-900/60 to-slate-900/80', tag: 'Chill' },
    { id: 'p2', title: 'Anirudh High Voltage', artist: 'Anirudh Ravichander', tracks: 32, bg: 'from-red-900/60 to-slate-900/80', tag: 'Energized' },
    { id: 'p3', title: 'Rahman Melodic Deep Focus', artist: 'A.R. Rahman', tracks: 40, bg: 'from-violet-900/60 to-slate-900/80', tag: 'Focus' },
    { id: 'p4', title: 'Monsoon Acoustic Drift', artist: 'Sid Sriram & Pradeep', tracks: 18, bg: 'from-cyan-900/60 to-slate-900/80', tag: 'Calm' }
  ];

  return (
    <div className="w-full space-y-3">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Library className="w-4 h-4 text-cyan-400" />
          <span>Connected Music Libraries (Spotify & YouTube)</span>
        </h3>
        <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
          <Sparkles className="w-3 h-3 text-cyan-400" /> Synced
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {playlists.map(p => (
          <GlassCard
            key={p.id}
            hoverable
            onClick={() => onSelectMoodTag(p.tag)}
            className="p-3.5 space-y-3 relative group overflow-hidden border border-slate-800 hover:border-cyan-500/40"
          >
            <div className={`w-full aspect-square rounded-xl bg-gradient-to-br ${p.bg} flex items-center justify-center relative overflow-hidden shadow-inner`}>
              <Disc3 className="w-10 h-10 text-white/40 group-hover:rotate-45 transition-transform duration-500" />
              <div className="absolute top-2 right-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-black/60 text-cyan-300 border border-white/10">
                {p.tag}
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-white truncate group-hover:text-cyan-300 transition-colors">
                {p.title}
              </h4>
              <p className="text-[11px] text-slate-400 truncate mt-0.5">{p.artist}</p>
              <span className="text-[10px] text-slate-500">{p.tracks} tracks</span>
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  );
};
