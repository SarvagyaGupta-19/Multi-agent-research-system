"use client";

import React, { useState } from "react";
import { GlassCard } from "../ui/GlassCard";
import { CheckCircle, XCircle, HelpCircle, Link as LinkIcon, FileText, AlertCircle, Server } from "lucide-react";
import ReactMarkdown from "react-markdown";

type TabId = "fact_check" | "analysis" | "sources" | "raw_data" | "log";

interface TabSystemProps {
  claims: any[];
  analysis: string;
  sources: any[];
  rawData: string;
  errors: string[];
}

export function TabSystem({ claims, analysis, sources, rawData, errors }: TabSystemProps) {
  const [activeTab, setActiveTab] = useState<TabId>("fact_check");

  const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
    { id: "fact_check", label: "Fact-Check Results", icon: CheckCircle },
    { id: "analysis", label: "Analysis", icon: BarChartIcon },
    { id: "sources", label: "Sources", icon: LinkIcon },
    { id: "raw_data", label: "Raw Data", icon: FileText },
    { id: "log", label: "Pipeline Log", icon: Server },
  ];

  return (
    <div className="w-full mt-12 flex flex-col">
      <div className="flex space-x-2 border-b border-slate-800 pb-2 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-t-lg transition-colors whitespace-nowrap ${
                isActive 
                  ? "bg-slate-800/80 text-cyan-400 border-b-2 border-cyan-400" 
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="font-mono text-sm font-semibold">{tab.label.toUpperCase()}</span>
            </button>
          );
        })}
      </div>

      <div className="pt-6">
        {activeTab === "fact_check" && <FactCheckTab claims={claims} />}
        {activeTab === "analysis" && <AnalysisTab analysis={analysis} />}
        {activeTab === "sources" && <SourcesTab sources={sources} />}
        {activeTab === "raw_data" && <RawDataTab data={rawData} />}
        {activeTab === "log" && <PipelineLogTab errors={errors} />}
      </div>
    </div>
  );
}

function FactCheckTab({ claims }: { claims: any[] }) {
  if (!claims || claims.length === 0) return <div className="text-slate-500 font-mono text-sm">No claims extracted.</div>;

  // Sort: Unverified -> Uncertain -> Verified
  const sortedClaims = [...claims].sort((a, b) => {
    const rank = { unverified: 0, uncertain: 1, verified: 2 };
    return (rank[a.status as keyof typeof rank] ?? 3) - (rank[b.status as keyof typeof rank] ?? 3);
  });

  return (
    <div className="space-y-4">
      {sortedClaims.map((claim, idx) => {
        const isVerified = claim.status === "verified";
        const isUnverified = claim.status === "unverified";
        
        let borderClass = "border-amber-500/50";
        let icon = <HelpCircle className="w-5 h-5 text-amber-500 mt-1 shrink-0" />;
        
        if (isVerified) {
          borderClass = "border-emerald-500/50";
          icon = <CheckCircle className="w-5 h-5 text-emerald-500 mt-1 shrink-0" />;
        } else if (isUnverified) {
          borderClass = "border-red-500/50";
          icon = <XCircle className="w-5 h-5 text-red-500 mt-1 shrink-0" />;
        }

        return (
          <GlassCard key={idx} className={`border-l-4 ${borderClass} p-4`}>
            <div className="flex items-start space-x-3">
              {icon}
              <div className="flex-1">
                <p className="text-slate-200 font-medium">{claim.claim}</p>
                <p className="text-slate-400 text-sm mt-2">{claim.rationale}</p>
                {claim.source && claim.source !== "No source" && (
                  <div className="mt-3 flex items-center space-x-2 text-xs font-mono">
                    <LinkIcon className="w-3 h-3 text-cyan-500" />
                    <a href={claim.source} target="_blank" rel="noreferrer" className="text-cyan-500 hover:underline truncate max-w-md">
                      {claim.source}
                    </a>
                  </div>
                )}
              </div>
            </div>
          </GlassCard>
        );
      })}
    </div>
  );
}

function AnalysisTab({ analysis }: { analysis: string }) {
  if (!analysis) return <div className="text-slate-500 font-mono text-sm">No analysis available.</div>;
  return (
    <GlassCard className="p-6 prose prose-invert prose-cyan max-w-none">
      <ReactMarkdown>{analysis}</ReactMarkdown>
    </GlassCard>
  );
}

function SourcesTab({ sources }: { sources: any[] }) {
  if (!sources || sources.length === 0) return <div className="text-slate-500 font-mono text-sm">No sources available.</div>;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {sources.map((source, idx) => (
        <GlassCard key={idx} className="p-4 flex flex-col">
          <div className="flex items-start space-x-2 mb-2">
            <LinkIcon className="w-4 h-4 text-cyan-500 mt-1 shrink-0" />
            <a href={source.url} target="_blank" rel="noreferrer" className="text-cyan-400 font-medium hover:underline line-clamp-2">
              {source.title}
            </a>
          </div>
          <p className="text-slate-400 text-sm flex-1 line-clamp-3">{source.snippet}</p>
          <div className="mt-3 text-xs text-slate-600 font-mono truncate">{source.url}</div>
        </GlassCard>
      ))}
    </div>
  );
}

function RawDataTab({ data }: { data: string }) {
  return (
    <GlassCard className="p-0 overflow-hidden flex flex-col h-[600px]">
      <div className="bg-slate-900/80 p-2 border-b border-slate-800 text-xs font-mono text-slate-500 flex justify-between">
        <span>RAW_RESEARCH_DUMP.TXT</span>
        <span>{data.length} bytes</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <pre className="text-xs font-mono text-slate-400 whitespace-pre-wrap break-words">
          {data || "No raw data."}
        </pre>
      </div>
    </GlassCard>
  );
}

function PipelineLogTab({ errors }: { errors: string[] }) {
  if (!errors || errors.length === 0) {
    return (
      <GlassCard className="p-6 flex flex-col items-center justify-center text-center space-y-4 h-40">
        <CheckCircle className="w-8 h-8 text-emerald-500/50" />
        <div className="font-mono text-emerald-500/80 text-sm">PIPELINE_COMPLETE_NO_ISSUES</div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-2">
      {errors.map((err, idx) => (
        <div key={idx} className="bg-slate-900/50 border border-amber-900/30 p-3 rounded text-sm font-mono text-amber-200/80 flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
          <span>{err}</span>
        </div>
      ))}
    </div>
  );
}

// Helper icon
function BarChartIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" x2="18" y1="20" y2="10" />
      <line x1="12" x2="12" y1="20" y2="4" />
      <line x1="6" x2="6" y1="20" y2="14" />
    </svg>
  );
}
