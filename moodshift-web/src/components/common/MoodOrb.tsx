import React from 'react';

export interface MoodOrbProps {
  energy: number;   // 0.0 to 1.0
  valence: number;  // 0.0 to 1.0
  arousal: number;  // 0.0 to 1.0
  size?: 'sm' | 'md' | 'lg' | 'hero';
  className?: string;
  isPulsing?: boolean;
}

export const MoodOrb: React.FC<MoodOrbProps> = ({
  energy,
  valence,
  arousal,
  size = 'md',
  className = '',
  isPulsing = true
}) => {
  // Dimensions
  const sizeMap = {
    sm: 'w-16 h-16',
    md: 'w-28 h-28',
    lg: 'w-44 h-44',
    hero: 'w-64 h-64'
  };

  // Color gradient interpolation based on Valence & Energy
  // High valence + high energy: Vibrant Amber -> Cyan -> Emerald
  // Low valence + low energy: Deep Indigo -> Midnight Slate -> Violet
  const getGradientColors = () => {
    if (valence > 0.6 && energy > 0.6) {
      return {
        c1: '#F59E0B', // Amber
        c2: '#06B6D4', // Cyan
        c3: '#10B981', // Emerald
        glow: 'rgba(245, 158, 11, 0.45)'
      };
    }
    if (valence > 0.6 && energy <= 0.6) {
      return {
        c1: '#06B6D4', // Cyan
        c2: '#3B82F6', // Blue
        c3: '#10B981', // Emerald
        glow: 'rgba(6, 182, 212, 0.4)'
      };
    }
    if (valence <= 0.4 && energy > 0.6) {
      return {
        c1: '#EF4444', // Red
        c2: '#F97316', // Orange
        c3: '#8B5CF6', // Violet
        glow: 'rgba(239, 68, 68, 0.4)'
      };
    }
    // Low valence + low energy (reflective / sad / tired)
    return {
      c1: '#6366F1', // Indigo
      c2: '#8B5CF6', // Violet
      c3: '#1E293B', // Slate
      glow: 'rgba(99, 102, 241, 0.35)'
    };
  };

  const colors = getGradientColors();
  const pulseDuration = `${Math.max(1.8, 6.0 - (energy * 3.8))}s`;
  const glowSpread = `${Math.max(15, arousal * 45)}px`;

  return (
    <div
      className={`relative rounded-full flex items-center justify-center shrink-0 ${sizeMap[size]} ${className}`}
      style={{
        boxShadow: `0 0 ${glowSpread} ${colors.glow}`
      }}
    >
      {/* Outer ambient breathing ring */}
      <div
        className={`absolute inset-0 rounded-full opacity-60 filter blur-xl ${isPulsing ? 'animate-pulse' : ''}`}
        style={{
          background: `radial-gradient(circle, ${colors.c1} 0%, ${colors.c2} 50%, transparent 80%)`,
          animationDuration: pulseDuration
        }}
      />

      {/* Main Fluid Sphere */}
      <div
        className={`w-full h-full rounded-full relative overflow-hidden backdrop-blur-sm border border-white/20 ${isPulsing ? 'animate-orb-float' : ''}`}
        style={{
          background: `linear-gradient(135deg, ${colors.c1} 0%, ${colors.c2} 55%, ${colors.c3} 100%)`,
          animationDuration: pulseDuration
        }}
      >
        {/* Specular highlight */}
        <div className="absolute top-2 left-3 w-1/3 h-1/4 rounded-full bg-white/40 filter blur-[2px] transform -rotate-12" />
        
        {/* Internal fluid depth */}
        <div
          className="absolute inset-0 rounded-full mix-blend-overlay opacity-50"
          style={{
            background: 'radial-gradient(circle at 30% 30%, rgba(255,255,255,0.8), transparent 70%)'
          }}
        />
      </div>
    </div>
  );
};
