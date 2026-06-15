"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "@/components/ui/GlassCard";
import { PipelineVisualizer } from "@/components/pipeline/PipelineVisualizer";
import { TrustScoreGauge } from "@/components/results/TrustScoreGauge";
import { ReportRenderer } from "@/components/results/ReportRenderer";
import { TabSystem } from "@/components/results/TabSystem";
import { submitResearchJob, pollJobStatus, JobStatusResponse } from "@/lib/api";
import { Database, Search, ChevronRight, AlertTriangle, Download, Copy, RefreshCw, Activity, ArrowRight, CheckCircle2 } from "lucide-react";

type AppState = "INPUT" | "PROCESSING" | "RESULTS" | "ERROR";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("INPUT");
  const [topic, setTopic] = useState("");
  const [style, setStyle] = useState("academic");
  const [model, setModel] = useState("llama-3.3-70b-versatile");
  const [skipMemory, setSkipMemory] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobData, setJobData] = useState<JobStatusResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  
  const [stageIndex, setStageIndex] = useState(0);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const stageIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const startResearch = async () => {
    if (!topic.trim()) return;
    try {
      setAppState("PROCESSING");
      setStageIndex(0);
      
      const sessionId = localStorage.getItem("research_session_id") || crypto.randomUUID();
      localStorage.setItem("research_session_id", sessionId);

      const response = await submitResearchJob({
        topic,
        style,
        model,
        skip_memory: skipMemory,
        session_id: sessionId,
      });

      setJobId(response.job_id);

      stageIntervalRef.current = setInterval(() => {
        setStageIndex(prev => (prev < 6 ? prev + 1 : prev));
      }, 8000); 

      pollingRef.current = setInterval(async () => {
        try {
          const statusRes = await pollJobStatus(response.job_id);
          if (statusRes.status === "complete") {
            clearInterval(pollingRef.current!);
            clearInterval(stageIntervalRef.current!);
            setStageIndex(7);
            setJobData(statusRes);
            setTimeout(() => setAppState("RESULTS"), 500);
          } else if (statusRes.status === "failed") {
            clearInterval(pollingRef.current!);
            clearInterval(stageIntervalRef.current!);
            setErrorMsg(statusRes.error || "Research job failed");
            setAppState("ERROR");
          }
        } catch (err: any) {
          clearInterval(pollingRef.current!);
          clearInterval(stageIntervalRef.current!);
          setErrorMsg(err.message || "Failed to poll job status");
          setAppState("ERROR");
        }
      }, 2000);

    } catch (err: any) {
      setErrorMsg(err.message || "Failed to start research");
      setAppState("ERROR");
    }
  };

  const reset = () => {
    setAppState("INPUT");
    setTopic("");
    setJobData(null);
    setJobId(null);
    setErrorMsg("");
    if (pollingRef.current) clearInterval(pollingRef.current);
    if (stageIntervalRef.current) clearInterval(stageIntervalRef.current);
  };

  const copyReport = () => {
    if (jobData?.result?.report) {
      navigator.clipboard.writeText(jobData.result.report);
      alert("Report copied to clipboard!");
    }
  };

  const downloadReport = () => {
    if (jobData?.result?.report) {
      const blob = new Blob([jobData.result.report], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `research_${topic.replace(/\\s+/g, '_').toLowerCase()}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="flex flex-col min-h-screen w-full font-sans">
      
      {/* PROFESSIONAL NAV BAR */}
      <nav className="w-full border-b border-white/10 bg-black/40 backdrop-blur-md px-6 py-4 flex items-center justify-between z-50">
        <div className="flex items-center space-x-3">
          <Database className="w-5 h-5 text-slate-300" />
          <span className="font-heading font-bold text-lg tracking-wide text-white">Multi Agent Researcher</span>
        </div>
        <div className="hidden md:flex space-x-6 text-sm font-medium text-slate-400">
          <a 
            href="https://github.com/SarvagyaGupta-19/Multi-agent-research-system" 
            target="_blank" 
            rel="noopener noreferrer"
            className="hover:text-white cursor-pointer transition-colors"
          >
            Documentation
          </a>
        </div>
      </nav>

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <AnimatePresence mode="wait">
          
          {/* INPUT STATE */}
          {appState === "INPUT" && (
            <motion.div
              key="input"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="w-full max-w-4xl"
            >
              <div className="mb-12 text-center md:text-left">
                <h1 className="text-4xl md:text-5xl font-heading font-medium text-white mb-4 tracking-tight">
                  Synthesize Global Knowledge.
                </h1>
                <p className="text-lg text-slate-400 max-w-2xl font-light">
                  Query our autonomous research cluster to aggregate, analyze, and fact-check data across the web in real-time.
                </p>
              </div>

              <GlassCard className="p-1 border border-white/10 bg-black/50 shadow-2xl overflow-visible">
                <div className="bg-black/80 rounded-xl p-6 md:p-8">
                  
                  {/* Search Bar */}
                  <div className="relative mb-8">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <Search className="w-6 h-6 text-slate-500" />
                    </div>
                    <input
                      type="text"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="Enter research query (e.g., Economic impact of quantum computing in logistics)"
                      className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-12 pr-4 py-4 text-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-400 transition-colors"
                      onKeyDown={(e) => e.key === 'Enter' && startResearch()}
                    />
                  </div>

                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                    <div className="w-full md:w-auto flex flex-col md:flex-row gap-6">
                      {/* Output Style Selection */}
                      <div>
                        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Synthesis Format</label>
                        <div className="flex flex-wrap gap-2">
                          {["academic", "blog", "executive summary", "technical"].map((s) => (
                            <button
                              key={s}
                              onClick={() => setStyle(s)}
                              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                                style === s 
                                  ? "bg-white text-black" 
                                  : "bg-slate-800/50 text-slate-300 border border-slate-700 hover:bg-slate-700"
                              }`}
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Model Selection */}
                      <div>
                        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">LLM Model</label>
                        <select 
                          value={model}
                          onChange={(e) => setModel(e.target.value)}
                          className="bg-slate-800/50 text-slate-300 border border-slate-700 hover:bg-slate-700 px-4 py-2.5 rounded-md text-sm font-medium transition-colors outline-none cursor-pointer h-[38px]"
                        >
                          <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
                          <option value="llama3-8b-8192">Llama 3 8B (Fast)</option>
                        </select>
                      </div>
                    </div>

                    {/* Execute Button */}
                    <button
                      onClick={startResearch}
                      disabled={!topic.trim()}
                      className="w-full md:w-auto flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white font-medium px-8 py-3 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span>Run Synthesis</span>
                      <ArrowRight className="w-5 h-5" />
                    </button>
                  </div>

                  <div className="mt-8 pt-6 border-t border-slate-800 flex items-center justify-between">
                     <label className="flex items-center space-x-3 cursor-pointer group">
                      <div className={`w-5 h-5 rounded flex items-center justify-center transition-colors border ${!skipMemory ? 'bg-blue-600 border-blue-500' : 'bg-slate-900 border-slate-700'}`}>
                        {!skipMemory && <CheckCircle2 className="w-3 h-3 text-white" />}
                      </div>
                      <input 
                        type="checkbox" 
                        className="hidden"
                        checked={!skipMemory} 
                        onChange={(e) => setSkipMemory(!e.target.checked)}
                      />
                      <span className="text-sm font-medium text-slate-400 group-hover:text-slate-200 transition-colors">Enable Contextual Memory</span>
                    </label>

                    <div className="hidden md:flex space-x-6">
                       <span className="flex items-center text-xs text-slate-500"><Activity className="w-3 h-3 mr-1" /> Live Indexing</span>
                       <span className="flex items-center text-xs text-slate-500"><CheckCircle2 className="w-3 h-3 mr-1" /> Fact Checked</span>
                    </div>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          )}

          {/* PROCESSING STATE */}
          {appState === "PROCESSING" && (
            <motion.div
              key="processing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full max-w-5xl flex flex-col items-center"
            >
              <div className="mb-10 text-center">
                <h2 className="text-xl font-heading text-slate-200 mb-2 font-medium flex items-center justify-center">
                  <Activity className="w-5 h-5 mr-3 text-blue-400 animate-pulse" />
                  Aggregating Data
                </h2>
                <p className="text-slate-400 text-lg font-light max-w-2xl mx-auto truncate">{topic}</p>
              </div>
              
              <GlassCard className="w-full py-12 px-8 border border-slate-700/50 bg-black/60 shadow-xl">
                <PipelineVisualizer currentStageIndex={stageIndex} />
              </GlassCard>
              
              <button 
                onClick={reset}
                className="mt-10 text-sm font-medium text-slate-500 hover:text-red-400 transition-colors"
              >
                Cancel Operation
              </button>
            </motion.div>
          )}

          {/* ERROR STATE */}
          {appState === "ERROR" && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="w-full max-w-2xl"
            >
              <GlassCard className={`p-8 border bg-black/80 ${errorMsg.includes('Rate Limit Exceeded') ? 'border-amber-500/50' : 'border-red-900/50'}`}>
                <div className={`flex items-center space-x-3 mb-4 ${errorMsg.includes('Rate Limit Exceeded') ? 'text-amber-400' : 'text-red-400'}`}>
                  <AlertTriangle className="w-8 h-8" />
                  <h2 className="text-2xl font-heading font-medium">
                    {errorMsg.includes('Rate Limit Exceeded') ? 'Rate Limit Reached' : 'Operation Failed'}
                  </h2>
                </div>
                <p className="text-slate-300 mb-8 font-mono bg-slate-900/80 p-4 rounded-md text-sm border border-slate-800 leading-relaxed">
                  {errorMsg}
                </p>
                <button
                  onClick={reset}
                  className="bg-white hover:bg-slate-200 text-black font-medium px-6 py-2 rounded-md transition-colors"
                >
                  Return to Search
                </button>
              </GlassCard>
            </motion.div>
          )}

          {/* RESULTS STATE */}
          {appState === "RESULTS" && jobData?.result && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-6xl"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                <div>
                  <h1 className="text-3xl font-heading font-medium text-white leading-tight mb-2">{topic}</h1>
                  <div className="flex items-center space-x-4 text-sm text-slate-400">
                    <span className="uppercase tracking-wider font-semibold">Format: {style}</span>
                    <span>•</span>
                    <span>Completed: {new Date(jobData.updated_at).toLocaleString()}</span>
                    {!skipMemory && jobData.result.memory_context && (
                      <>
                        <span>•</span>
                        <span className="text-blue-400 flex items-center"><Database className="w-3 h-3 mr-1" /> Context Applied</span>
                      </>
                    )}
                  </div>
                </div>
                <button 
                  onClick={reset} 
                  className="flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors w-fit"
                >
                  <Search className="w-4 h-4" />
                  <span>New Query</span>
                </button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
                <GlassCard className="lg:col-span-1 flex flex-col items-center justify-center p-6 border border-slate-700/50 bg-black/60">
                  <h3 className="text-xs font-semibold text-slate-400 mb-2 tracking-widest uppercase w-full text-center border-b border-slate-800 pb-2">Confidence Score</h3>
                  <TrustScoreGauge 
                    score={jobData.result.fact_checked_report ? JSON.parse(jobData.result.fact_checked_report).trust_score : 0} 
                    verified={jobData.result.claims?.filter((c:any) => c.status === "verified").length || 0}
                    total={jobData.result.claims?.length || 0}
                  />
                </GlassCard>
                
                <div className="lg:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: "SOURCES ANALYZED", val: jobData.result.sources?.length || 0 },
                    { label: "CLAIMS VERIFIED", val: jobData.result.claims?.filter((c:any) => c.status === "verified").length || 0 },
                    { label: "CLAIMS UNVERIFIED", val: jobData.result.claims?.filter((c:any) => c.status !== "verified").length || 0, color: 'text-amber-400' },
                    { label: "PIPELINE ERRORS", val: jobData.result.errors?.length || 0, color: jobData.result.errors?.length > 0 ? 'text-red-400' : 'text-slate-200' },
                  ].map((stat, i) => (
                    <GlassCard key={i} className="p-5 flex flex-col justify-center border border-slate-700/50 bg-black/60">
                      <div className="text-xs font-semibold text-slate-400 mb-3 tracking-wider uppercase">{stat.label}</div>
                      <div className={`text-4xl font-light ${stat.color || 'text-white'}`}>
                        {stat.val}
                      </div>
                    </GlassCard>
                  ))}
                </div>
              </div>

              {/* MAIN REPORT */}
              <GlassCard className="p-8 md:p-12 mb-8 border border-slate-700/50 bg-black/80">
                <div className="flex justify-between items-center mb-8 pb-4 border-b border-slate-800">
                  <h2 className="text-xl font-heading font-medium text-white">Synthesized Output</h2>
                  <div className="flex space-x-2">
                    <button onClick={copyReport} className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md transition-colors">
                      <Copy className="w-4 h-4" />
                      <span className="hidden sm:inline">Copy</span>
                    </button>
                    <button onClick={downloadReport} className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-md transition-colors">
                      <Download className="w-4 h-4" />
                      <span className="hidden sm:inline">Export</span>
                    </button>
                  </div>
                </div>
                <div className="text-lg">
                  <ReportRenderer content={jobData.result.report || "No report generated."} />
                </div>
              </GlassCard>

              {/* TABS */}
              <div className="mb-20">
                <TabSystem 
                  claims={jobData.result.claims || []}
                  analysis={jobData.result.analysis || ""}
                  sources={jobData.result.sources || []}
                  rawData={jobData.result.raw_research || ""}
                  errors={jobData.result.errors || []}
                />
              </div>

            </motion.div>
          )}

        </AnimatePresence>
      </main>
    </div>
  );
}
