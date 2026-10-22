import React from 'react';

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  hoverable?: boolean;
  glowColor?: string;
  variant?: 'default' | 'elevated' | 'subtle';
  className?: string;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  hoverable = false,
  glowColor,
  variant = 'default',
  className = '',
  style,
  ...props
}) => {
  const variantClass = variant === 'elevated' ? 'shadow-2xl border-white/10' : variant === 'subtle' ? 'border-white/5' : '';

  return (
    <div
      className={`glass-panel rounded-2xl p-5 ${hoverable ? 'glass-card-hover cursor-pointer' : ''} ${className}`}
      style={{
        boxShadow: glowColor ? `0 10px 30px -10px ${glowColor}33` : undefined,
        ...style
      }}
      {...props}
    >
      {children}
    </div>
  );
};
