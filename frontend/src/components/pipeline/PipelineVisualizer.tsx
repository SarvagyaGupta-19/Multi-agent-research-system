"use client";

import React from "react";
import { motion } from "framer-motion";
import { Brain, Search, Settings, BarChart2, PenTool, CheckCircle, Save, AlertCircle } from "lucide-react";

const STAGES = [
  { id: "memory_read", label: "Recalling Context", icon: Brain },
  { id: "researcher", label: "Searching Web", icon: Search },
  { id: "compress", label: "Processing", icon: Settings },
  { id: "analyst", label: "Analyzing", icon: BarChart2 },
  { id: "writer", label: "Writing", icon: PenTool },
  { id: "fact_checker", label: "Verifying", icon: CheckCircle },
  { id: "memory_write", label: "Saving", icon: Save },
];

interface PipelineVisualizerProps {
  currentStageIndex: number;
  hasError?: boolean;
}

export function PipelineVisualizer({ currentStageIndex, hasError = false }: PipelineVisualizerProps) {
  return (
    <div className="w-full max-w-4xl mx-auto p-8">
      <div className="relative flex justify-between items-center w-full">
        {/* Background connecting line */}
        <div className="absolute top-1/2 left-0 w-full h-1 bg-slate-800 -translate-y-1/2 z-0 rounded" />
        
        {/* Active connecting line */}
        <motion.div 
          className="absolute top-1/2 left-0 h-1 bg-cyan-400 -translate-y-1/2 z-0 rounded shadow-[0_0_10px_rgba(34,211,238,0.8)]"
          initial={{ width: "0%" }}
          animate={{ width: `${(Math.min(currentStageIndex, STAGES.length - 1) / (STAGES.length - 1)) * 100}%` }}
          transition={{ duration: 0.5 }}
        />

        {STAGES.map((stage, index) => {
          const isActive = index === currentStageIndex;
          const isComplete = index < currentStageIndex;
          const isErrorNode = isActive && hasError;

          let iconColor = "text-slate-500";
          let bgColor = "bg-slate-900/80";
          let borderColor = "border-slate-700";

          if (isComplete) {
            iconColor = "text-white";
            bgColor = "bg-blue-600";
            borderColor = "border-blue-500";
          } else if (isActive) {
            if (isErrorNode) {
              iconColor = "text-white";
              bgColor = "bg-red-600";
              borderColor = "border-red-500";
            } else {
              iconColor = "text-blue-400";
              bgColor = "bg-slate-800";
              borderColor = "border-blue-500";
            }
          }

          const Icon = stage.icon;

          return (
            <div key={stage.id} className="relative z-10 flex flex-col items-center">
              <motion.div 
                className={`w-12 h-12 rounded-full border flex items-center justify-center ${bgColor} ${borderColor} transition-colors duration-300 shadow-lg`}
                animate={isActive && !isErrorNode ? { scale: [1, 1.05, 1] } : { scale: 1 }}
                transition={isActive ? { repeat: Infinity, duration: 2 } : {}}
              >
                {isErrorNode ? <AlertCircle className="w-5 h-5 text-white" /> : <Icon className={`w-5 h-5 ${iconColor}`} />}
              </motion.div>
              <div className={`mt-3 text-xs font-semibold uppercase tracking-wider absolute -bottom-8 whitespace-nowrap ${isActive ? (isErrorNode ? "text-red-400" : "text-blue-400") : isComplete ? "text-slate-300" : "text-slate-600"}`}>
                {stage.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
