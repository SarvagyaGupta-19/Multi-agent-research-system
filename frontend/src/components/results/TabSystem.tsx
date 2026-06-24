"use client";

import React, { useState } from "react";
import { ScrapbookCard } from "../ui/ScrapbookCard";
import { CheckCircle, XCircle, HelpCircle, Link as LinkIcon, FileText, AlertCircle, Server } from "lucide-react";
import ReactMarkdown from "react-markdown";

type TabId = "fact_check" | "analysis" | "sources";

interface TabSystemProps {
  claims: any[];
  analysis: string;
  sources: any[];
}

export function TabSystem({ claims, analysis, sources }: TabSystemProps) {
  const [activeTab, setActiveTab] = useState<TabId>("fact_check");

  const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
    { id: "fact_check", label: "Fact-Check Results", icon: CheckCircle },
    { id: "analysis", label: "Analysis", icon: BarChartIcon },
    { id: "sources", label: "Sources", icon: LinkIcon },
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
                  ? "bg-gray-900 text-white shadow-md border-b-2 border-gray-900"
                  : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
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
      </div>
    </div>
  );
}

function FactCheckTab({ claims }: { claims: any[] }) {
  if (!claims || claims.length === 0) return <div className="text-gray-500 font-mono text-sm">No claims extracted.</div>;

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
          <ScrapbookCard key={idx} className={`border-l-8 ${borderClass} p-4`}>
            <div className="flex space-x-3">
              {icon}
              <div className="flex-1">
                <p className="text-gray-800 font-medium">{claim.claim}</p>
                <p className="text-gray-600 text-sm mt-2">{claim.rationale}</p>
                {claim.source && claim.source !== "No source" && (
                  <div className="mt-3 flex items-center space-x-2 text-xs font-mono">
                    <LinkIcon className="w-3 h-3 text-cyan-600" />
                    <a href={claim.source} target="_blank" rel="noreferrer" className="text-cyan-600 hover:underline truncate max-w-md">
                      {claim.source}
                    </a>
                  </div>
                )}
              </div>
            </div>
          </ScrapbookCard>
        );
      })}
    </div>
  );
}

function AnalysisTab({ analysis }: { analysis: string }) {
  if (!analysis) return <div className="text-gray-500 font-mono text-sm">No analysis available.</div>;
  return (
    <ScrapbookCard className="p-6 prose max-w-none">
      <div className="text-gray-800">{analysis}</div>
    </ScrapbookCard>
  );
}

function SourcesTab({ sources }: { sources: any[] }) {
  if (!sources || sources.length === 0) return <div className="text-gray-500 font-mono text-sm">No sources available.</div>;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {sources.map((source, idx) => (
        <ScrapbookCard key={idx} className="p-4 flex flex-col">
          <div className="flex space-x-2 mb-2">
            <LinkIcon className="w-4 h-4 text-cyan-600 mt-1 shrink-0" />
            <a href={source.url} target="_blank" rel="noreferrer" className="text-cyan-600 font-medium hover:underline line-clamp-2">
              {source.title}
            </a>
          </div>
          <p className="text-gray-600 text-sm flex-1 line-clamp-3">{source.snippet}</p>
          <div className="mt-3 text-xs text-gray-400 font-mono truncate">{source.url}</div>
        </ScrapbookCard>
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
