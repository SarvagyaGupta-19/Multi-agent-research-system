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
        <div className="absolute top-1/2 left-0 w-full h-1 bg-gray-200 -translate-y-1/2 z-0 rounded" />
        
        {/* Active connecting line */}
        <motion.div 
          className="absolute top-1/2 left-0 h-1 bg-gray-900 -translate-y-1/2 z-0 rounded"
          initial={{ width: "0%" }}
          animate={{ width: `${(Math.min(currentStageIndex, STAGES.length - 1) / (STAGES.length - 1)) * 100}%` }}
          transition={{ duration: 0.5 }}
        />

        {STAGES.map((stage, index) => {
          const isActive = index === currentStageIndex;
          const isComplete = index < currentStageIndex;
          const isErrorNode = isActive && hasError;

          let iconColor = "text-gray-500";
          let bgColor = "bg-white";
          let borderColor = "border-gray-200";

          if (isComplete) {
            iconColor = "text-gray-900";
            bgColor = "bg-[#b9ff66]";
            borderColor = "border-gray-900";
          } else if (isActive) {
            if (isErrorNode) {
              iconColor = "text-white";
              bgColor = "bg-red-500";
              borderColor = "border-red-500";
            } else {
              iconColor = "text-gray-900";
              bgColor = "bg-[#ff90e8]";
              borderColor = "border-gray-900";
            }
          }

          const Icon = stage.icon;

          return (
            <div key={stage.id} className="relative z-10 flex flex-col items-center">
              <motion.div 
                className={`w-12 h-12 rounded-full border-2 flex items-center justify-center ${bgColor} ${borderColor} transition-colors duration-300 ${isActive || isComplete ? 'shadow-[2px_2px_0px_0px_rgba(26,26,26,1)]' : ''}`}
                animate={isActive && !isErrorNode ? { scale: [1, 1.1, 1], rotate: [0, -5, 5, 0] } : { scale: 1 }}
                transition={isActive ? { repeat: Infinity, duration: 2 } : {}}
              >
                {isErrorNode ? <AlertCircle className="w-5 h-5 text-white" /> : <Icon className={`w-5 h-5 ${iconColor}`} />}
              </motion.div>
              <div className={`mt-3 text-[10px] sm:text-xs font-bold uppercase tracking-widest absolute -bottom-10 text-center w-24 leading-tight ${isActive ? (isErrorNode ? "text-red-500" : "text-[#ff90e8]") : isComplete ? "text-gray-900" : "text-gray-400"}`}>
                {stage.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
