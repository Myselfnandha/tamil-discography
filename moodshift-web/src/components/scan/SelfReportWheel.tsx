import React, { useState, useRef, useCallback, useEffect } from 'react';
import { GlassCard } from '../common/GlassCard';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Sparkles, X, Compass, Check } from 'lucide-react';

interface SelfReportWheelProps {
  initialEnergy?: number;
  initialValence?: number;
  onConfirm: (energy: number, valence: number) => void;
  onCancel: () => void;
}

export const SelfReportWheel: React.FC<SelfReportWheelProps> = ({
  initialEnergy = 0.5,
  initialValence = 0.5,
  onConfirm,
  onCancel
}) => {
  const [valence, setValence] = useState(initialValence);
  const [energy, setEnergy] = useState(initialEnergy);
  const [isDragging, setIsDragging] = useState(false);
  const padRef = useRef<HTMLDivElement>(null);

  const updateFromCoords = useCallback((clientX: number, clientY: number) => {
    if (!padRef.current) return;
    const rect = padRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, clientY - rect.top));

    // Valence: 0.0 (left) to 1.0 (right)
    const newV = Math.round((x / rect.width) * 100) / 100;
    // Energy: 1.0 (top) to 0.0 (bottom)
    const newE = Math.round((1 - y / rect.height) * 100) / 100;

    setValence(newV);
    setEnergy(newE);
  }, []);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
    updateFromCoords(e.clientX, e.clientY);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isDragging) {
      updateFromCoords(e.clientX, e.clientY);
    }
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    setIsDragging(false);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // Ignore if pointer capture already released
    }
  };

  const getQuadrantLabel = (e: number, v: number): { label: string; color: string; desc: string } => {
    if (e >= 0.5 && v >= 0.5) {
      return { label: 'Energized & Vibrant', color: 'emerald', desc: 'High drive, positive sentiment' };
    }
    if (e >= 0.5 && v < 0.5) {
      return { label: 'Tense & Overwhelmed', color: 'amber', desc: 'High drive, frustrated or anxious' };
    }
    if (e < 0.5 && v < 0.5) {
      return { label: 'Depleted & Down', color: 'purple', desc: 'Low energy, heavy or melancholic' };
    }
    return { label: 'Calm & Content', color: 'cyan', desc: 'Low energy, peaceful and grounded' };
  };

  const moodState = getQuadrantLabel(energy, valence);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <GlassCard className="w-full max-w-lg p-6 flex flex-col gap-6 shadow-2xl border-white/10" variant="elevated">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center border border-cyan-500/30">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">Self-Report Mood Wheel</h2>
              <p className="text-xs text-slate-400">Tap or drag inside the valence-energy 2D plane</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            aria-label="Close self report wheel"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 2D Interactive Grid */}
        <div className="relative">
          <div
            ref={padRef}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            className="relative w-full aspect-square rounded-2xl bg-gradient-to-br from-slate-900 via-slate-950 to-black border border-white/10 overflow-hidden cursor-crosshair select-none touch-none shadow-inner"
          >
            {/* Background quadrant tints */}
            <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 opacity-25 pointer-events-none">
              <div className="bg-amber-500/10 border-r border-b border-white/5 flex items-start justify-start p-3">
                <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">Tense / Anxious</span>
              </div>
              <div className="bg-emerald-500/10 border-b border-white/5 flex items-start justify-end p-3">
                <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Vibrant / Euphoric</span>
              </div>
              <div className="bg-purple-500/10 border-r border-white/5 flex items-end justify-start p-3">
                <span className="text-[10px] font-semibold text-purple-400 uppercase tracking-wider">Depleted / Gloomy</span>
              </div>
              <div className="bg-cyan-500/10 flex items-end justify-end p-3">
                <span className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">Calm / Peaceful</span>
              </div>
            </div>

            {/* Axes lines */}
            <div className="absolute top-1/2 left-0 right-0 h-px bg-white/10 pointer-events-none" />
            <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/10 pointer-events-none" />

            {/* Axis Labels */}
            <div className="absolute top-2 left-1/2 -translate-x-1/2 text-[10px] uppercase tracking-widest text-slate-500 font-bold pointer-events-none">
              Electric Energy (1.0)
            </div>
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-[10px] uppercase tracking-widest text-slate-500 font-bold pointer-events-none">
              Depleted Energy (0.0)
            </div>
            <div className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] uppercase tracking-widest text-slate-500 font-bold pointer-events-none -rotate-90">
              Negative Valence
            </div>
            <div className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] uppercase tracking-widest text-slate-500 font-bold pointer-events-none rotate-90">
              Positive Valence
            </div>

            {/* Draggable Point */}
            <div
              className="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-none transition-transform duration-75 ease-out"
              style={{
                left: `${valence * 100}%`,
                top: `${(1 - energy) * 100}%`
              }}
            >
              <div className="relative">
                <div className="w-8 h-8 rounded-full bg-cyan-400/30 animate-ping absolute inset-0 -m-1" />
                <div className="w-6 h-6 rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400 border-2 border-white shadow-lg flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-950" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Real-time State & Diagnostics */}
        <div className="p-4 rounded-xl bg-white/5 border border-white/5 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-white">{moodState.label}</span>
            <Badge variant="cyan" size="sm">
              Valence {Math.round(valence * 100)}% • Energy {Math.round(energy * 100)}%
            </Badge>
          </div>
          <p className="text-xs text-slate-400">{moodState.desc}</p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 justify-end">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => onConfirm(energy, valence)}
            icon={<Check className="w-4 h-4" />}
          >
            Apply Assessment
          </Button>
        </div>
      </GlassCard>
    </div>
  );
};
