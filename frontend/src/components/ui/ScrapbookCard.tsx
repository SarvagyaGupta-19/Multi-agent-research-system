import React from 'react';

interface ScrapbookCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  rotation?: number;
}

export function ScrapbookCard({ children, className = '', rotation = 0, ...props }: ScrapbookCardProps) {
  return (
    <div 
      className={`scrapbook-card ${className}`}
      style={{ transform: rotation ? `rotate(${rotation}deg)` : 'none' }}
      {...props}
    >
      <div style={{ transform: rotation ? `rotate(${-rotation}deg)` : 'none' }}>
        {children}
      </div>
    </div>
  );
}
