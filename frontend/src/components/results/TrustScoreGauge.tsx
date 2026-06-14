"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface TrustScoreGaugeProps {
  score: number; // 0.0 to 1.0
  verified: number;
  total: number;
}

export function TrustScoreGauge({ score, verified, total }: TrustScoreGaugeProps) {
  const [displayedScore, setDisplayedScore] = useState(0);
  const percentage = Math.round(score * 100);

  useEffect(() => {
    // Animate the number counting up
    let start = 0;
    const end = percentage;
    if (start === end) return;
    
    let totalDuration = 1200;
    let incrementTime = (totalDuration / end);
    
    let timer = setInterval(() => {
      start += 1;
      setDisplayedScore(start);
      if (start === end) clearInterval(timer);
    }, incrementTime);
    
    return () => clearInterval(timer);
  }, [percentage]);

  let colorClass = "text-red-500";
  let strokeClass = "stroke-red-500";
  let label = "Low Confidence";
  
  if (percentage >= 80) {
    colorClass = "text-emerald-400";
    strokeClass = "stroke-emerald-400";
    label = "High Confidence";
  } else if (percentage >= 50) {
    colorClass = "text-amber-400";
    strokeClass = "stroke-amber-400";
    label = "Moderate Confidence";
  }

  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-6">
      <div className="relative w-40 h-40 flex items-center justify-center">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 140 140">
          <circle
            className="stroke-slate-800"
            strokeWidth="12"
            fill="transparent"
            r={radius}
            cx="70"
            cy="70"
          />
          <motion.circle
            className={strokeClass}
            strokeWidth="12"
            strokeLinecap="round"
            fill="transparent"
            r={radius}
            cx="70"
            cy="70"
            initial={{ strokeDasharray: circumference, strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            style={{ 
              filter: `drop-shadow(0 0 8px currentColor)`
            }}
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className={`text-4xl font-bold font-mono ${colorClass}`}>{displayedScore}%</span>
        </div>
      </div>
      <div className="mt-4 text-center">
        <div className={`text-lg font-semibold ${colorClass}`}>{label}</div>
        <div className="text-sm text-slate-400 mt-1">{verified} of {total} claims verified</div>
      </div>
    </div>
  );
}
