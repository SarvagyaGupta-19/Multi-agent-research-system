import React from 'react';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  luminous?: boolean;
  elevation?: 1 | 2 | 3;
}

export function GlassCard({ children, className = '', luminous = false, elevation = 1, ...props }: GlassCardProps) {
  const baseClasses = luminous ? 'glass-panel-luminous' : 'glass-panel';
  
  // Opacity increases slightly with elevation
  const elevationBg = {
    1: 'bg-slate-900/40',
    2: 'bg-slate-900/60',
    3: 'bg-slate-900/80',
  }[elevation];

  return (
    <div 
      className={`rounded-xl overflow-hidden shadow-sm ${baseClasses} ${elevationBg} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
