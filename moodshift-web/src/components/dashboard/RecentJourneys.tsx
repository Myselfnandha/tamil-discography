import React from 'react';
import { GlassCard } from '../common/GlassCard';
import { History, CheckCircle2, Heart, ArrowRight } from 'lucide-react';

export const RecentJourneys: React.FC = () => {
  const journeys = [
    {
      id: 'j1',
      date: 'Yesterday, 8:45 PM',
      from: 'Stressed / Restless',
      to: 'Calm & Centered',
      tracksCount: 8,
      rating: 'Loved',
      color: '#06B6D4'
    },
    {
      id: 'j2',
      date: 'Monday, 9:15 AM',
      from: 'Low Energy / Foggy',
      to: 'Energized & Focused',
      tracksCount: 9,
      rating: 'Effective',
      color: '#EF4444'
    },
    {
      id: 'j3',
      date: 'Sunday, 10:30 PM',
      from: 'Overthinking',
      to: 'Wind Down',
      tracksCount: 7,
      rating: 'Fell Asleep',
      color: '#64748B'
    }
  ];

  return (
    <div className="w-full space-y-3">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <History className="w-4 h-4 text-cyan-400" />
          <span>Recent Mood Journeys</span>
        </h3>
        <span className="text-xs text-slate-500">Last 7 days</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {journeys.map(j => (
          <GlassCard key={j.id} hoverable className="p-4 space-y-2.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>{j.date}</span>
              <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{j.rating}</span>
              </span>
            </div>

            <div className="flex items-center gap-2 text-sm font-bold text-white">
              <span className="truncate">{j.from}</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span className="truncate" style={{ color: j.color }}>{j.to}</span>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-800">
              <span>{j.tracksCount} tracks completed</span>
              <span className="flex items-center gap-1 text-rose-400">
                <Heart className="w-3 h-3 fill-current" />
                Saved Preset
              </span>
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  );
};
