"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ScrapbookCard } from "@/components/ui/ScrapbookCard";
import { PipelineVisualizer } from "@/components/pipeline/PipelineVisualizer";
import { TrustScoreGauge } from "@/components/results/TrustScoreGauge";
import { ReportRenderer } from "@/components/results/ReportRenderer";
import { TabSystem } from "@/components/results/TabSystem";
import { submitResearchJob, pollJobStatus, JobStatusResponse } from "@/lib/api";
import { Search, AlertTriangle, Download, Copy, ArrowRight, CheckCircle2 } from "lucide-react";

type AppState = "INPUT" | "PROCESSING" | "RESULTS" | "ERROR";



export default function Home() {
  const [appState, setAppState] = useState<AppState>("INPUT");
  const [isInitializing, setIsInitializing] = useState(true);
  const [topic, setTopic] = useState("");
  const [style, setStyle] = useState("blog");
  const [model, setModel] = useState("llama-3.3-70b-versatile");
  const [skipMemory, setSkipMemory] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobData, setJobData] = useState<JobStatusResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  // Initial Loading Splash Screen
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsInitializing(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);
  
  const [stageIndex, setStageIndex] = useState(0);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const stageIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (appState === "RESULTS" && resultsRef.current) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [appState]);

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
      a.download = `research_${topic.replace(/\s+/g, '_').toLowerCase()}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="min-h-screen bg-[#fcfbf9] graph-paper-bg flex flex-col relative overflow-hidden font-sans">
      
      {/* Splash Screen Overlay */}
      <AnimatePresence>
        {isInitializing && (
          <motion.div
            key="splash"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.6, ease: "easeInOut" }}
            className="absolute inset-0 z-50 bg-[#fcfbf9] graph-paper-bg flex flex-col items-center justify-center overflow-hidden"
          >
            {/* Background background floating faces for splash */}
            <img src="/face_0_0.png" className="absolute top-[20%] left-[20%] w-20 opacity-30 mix-blend-multiply rotate-[-15deg] animate-pulse" alt="" />
            <img src="/face_3_2.png" className="absolute bottom-[20%] right-[20%] w-24 opacity-30 mix-blend-multiply rotate-12 animate-float" alt="" />
            <img src="/face_2_2.png" className="absolute top-[30%] right-[25%] w-16 opacity-30 mix-blend-multiply rotate-[25deg] animate-bounce" alt="" />

            <motion.div
              initial={{ scale: 0.5, rotate: -20, opacity: 0 }}
              animate={{ scale: 1, rotate: [0, 10, -10, 0], opacity: 1 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="w-32 h-32 mb-8 bg-white rounded-full border-4 border-gray-900 shadow-[6px_6px_0px_0px_rgba(26,26,26,1)] flex items-center justify-center relative z-10"
            >
              <img src="/face_1_1.png" className="w-[120%] h-[120%] object-contain mix-blend-multiply" alt="loading face" />
            </motion.div>
            
            <motion.h1 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="text-4xl md:text-5xl font-heading font-bold text-gray-900 z-10 flex flex-col items-center"
            >
              <span>Getting</span>
              <span className="highlight-pink mt-2 px-2 inline-block">creative...</span>
            </motion.h1>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Playful Nav Bar */}
      <nav className="w-full px-8 py-6 flex items-center justify-between z-50">
        <div className="flex items-center space-x-2">
          <span className="font-heading font-extrabold text-2xl tracking-tight text-gray-900">Multi Agent Research AI</span>
        </div>
      </nav>

      <main className="flex-1 flex flex-col items-center px-6 py-12 relative">
        
        {/* Background Canva Faces */}
        {appState === "INPUT" && (
          <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
             <img src="/face_0_0.png" alt="doodle" className="absolute top-20 left-[10%] w-24 opacity-80 mix-blend-multiply rotate-[-15deg] animate-pulse" />
             <img src="/face_1_1.png" alt="doodle" className="absolute bottom-40 left-[15%] w-20 opacity-80 mix-blend-multiply rotate-12 animate-float" />
             <img src="/face_2_2.png" alt="doodle" className="absolute top-32 right-[10%] w-28 opacity-80 mix-blend-multiply rotate-[20deg] animate-bounce" />
             <img src="/face_3_2.png" alt="doodle" className="absolute bottom-32 right-[15%] w-24 opacity-80 mix-blend-multiply rotate-[-5deg] animate-pulse" />
             <img src="/face_0_2.png" alt="doodle" className="absolute top-1/2 left-[5%] w-20 opacity-50 mix-blend-multiply animate-float-delayed" />
          </div>
        )}

        <AnimatePresence mode="wait">
          
          {/* INPUT STATE */}
          {appState === "INPUT" && (
            <motion.div
              key="input"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, y: -20 }}
              className="w-full max-w-5xl z-10 flex flex-col items-center"
            >
              <div className="mb-4 text-center max-w-3xl z-20">
                <h1 className="text-5xl md:text-6xl font-heading font-medium text-gray-900 mb-6 leading-tight">
                  Give your ideas a glow up. Meet your new <span className="highlight-pink font-bold">AI creative collaborator.</span>
                </h1>
                <p className="text-xl text-gray-600 font-medium">
                  Capture, organize, and elevate your ideas across work, life, and leisure.
                </p>
              </div>



              <div className="grid grid-cols-1 md:grid-cols-12 gap-8 w-full relative z-40 mt-6">
                
                {/* Main Search Input */}
                <ScrapbookCard className="md:col-span-8 p-6 md:p-8 z-20" rotation={-1}>
                  <div className="flex flex-col gap-4">
                    <label className="font-heading text-xl font-bold text-gray-900">What's on your mind?</label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search className="w-6 h-6 text-gray-400" />
                      </div>
                      <input
                        type="text"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        placeholder="e.g. Create a blog post outline about dopamine decorating"
                        className="w-full bg-gray-50 border-2 border-gray-200 rounded-xl pl-12 pr-4 py-4 text-lg text-gray-800 placeholder-gray-400 focus:outline-none focus:border-gray-900 focus:ring-0 transition-colors"
                        onKeyDown={(e) => e.key === 'Enter' && startResearch()}
                      />
                    </div>
                    {/* Integrated Memory Checkbox */}
                    <div className="mt-1 flex items-center bg-pink-50/50 p-2 rounded-lg border-2 border-pink-100">
                      <label className="flex items-center space-x-3 cursor-pointer group w-full px-2">
                        <div className={`w-5 h-5 rounded flex items-center justify-center transition-colors border-2 ${!skipMemory ? 'bg-[#ff90e8] border-gray-900' : 'bg-white border-gray-300'}`}>
                          {!skipMemory && <CheckCircle2 className="w-3 h-3 text-gray-900" strokeWidth={3} />}
                        </div>
                        <input 
                          type="checkbox" 
                          className="hidden"
                          checked={!skipMemory} 
                          onChange={(e) => setSkipMemory(!e.target.checked)}
                        />
                        <span className="text-sm font-bold text-gray-600 group-hover:text-gray-900 transition-colors">Remember this context for follow-up research</span>
                      </label>
                    </div>
                  </div>
                </ScrapbookCard>

                {/* Options Card */}
                <ScrapbookCard className="md:col-span-4 p-6 flex flex-col gap-6 z-10" rotation={2}>
                  <div>
                    <label className="block text-sm font-bold text-gray-900 uppercase tracking-wider mb-3">Format</label>
                    <div className="flex flex-wrap gap-2">
                      {["blog", "academic", "summary", "technical"].map((s) => (
                        <button
                          key={s}
                          onClick={() => setStyle(s)}
                          className={`px-4 py-2 rounded-full text-sm font-bold transition-all border-2 ${
                            style === s 
                              ? "bg-gray-900 text-white border-gray-900" 
                              : "bg-white text-gray-600 border-gray-200 hover:border-gray-900 hover:text-gray-900"
                          }`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-gray-900 uppercase tracking-wider mb-3">Model</label>
                    <select 
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="w-full bg-gray-50 text-gray-800 border-2 border-gray-200 hover:border-gray-900 px-4 py-3 rounded-xl text-sm font-bold transition-colors outline-none cursor-pointer appearance-none"
                    >
                      <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
                      <option value="llama-3.1-8b-instant">Llama 3.1 8B (Fast)</option>
                    </select>
                  </div>
                </ScrapbookCard>

                {/* Submit Action Area */}
                <div className="md:col-span-12 flex flex-col items-center mt-4 z-30">
                   <button
                      onClick={startResearch}
                      disabled={!topic.trim()}
                      className="group flex items-center justify-center space-x-3 bg-[#b9ff66] text-gray-900 font-bold text-xl px-12 py-5 rounded-full border-2 border-gray-900 shadow-[4px_4px_0px_0px_rgba(26,26,26,1)] transition-all hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(26,26,26,1)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-[4px_4px_0px_0px_rgba(26,26,26,1)]"
                    >
                      <span>Turn thoughts into reality</span>
                      <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
                    </button>
                </div>

              </div>
            </motion.div>
          )}

          {/* PROCESSING STATE */}
          {appState === "PROCESSING" && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="w-full max-w-4xl flex flex-col items-center z-10"
            >
              <div className="mb-12 text-center flex flex-col items-center">
                <motion.div
                  key={stageIndex}
                  initial={{ scale: 0.5, rotate: -20, opacity: 0 }}
                  animate={{ scale: 1, rotate: [0, 5, -5, 0], opacity: 1 }}
                  transition={{ duration: 0.5 }}
                  className="w-24 h-24 mb-6 bg-white rounded-full border-4 border-gray-900 shadow-[4px_4px_0px_0px_rgba(26,26,26,1)] flex items-center justify-center"
                >
                  <img 
                    src={[
                      "/face_0_2.png", // Recalling (thinking)
                      "/face_3_0.png", // Searching (surprised/discovering)
                      "/face_1_2.png", // Processing (tired/crunching)
                      "/face_3_2.png", // Analyzing (intense/analytical)
                      "/face_1_1.png", // Writing (smiling/flowing)
                      "/face_2_2.png", // Verifying (shocked/checking)
                      "/face_2_0.png", // Saving (happy/done)
                      "/face_2_0.png", // Fallback
                    ][Math.min(stageIndex, 7)]} 
                    className="w-[120%] h-[120%] object-contain mix-blend-multiply" 
                    alt="reaction" 
                  />
                </motion.div>
                <h2 className="text-4xl font-heading text-gray-900 mb-4 font-bold flex items-center justify-center h-12">
                  <AnimatePresence mode="wait">
                    <motion.span
                      key={stageIndex}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                    >
                      {[
                        "Hmm, let me remember...",
                        "Scouring the web...",
                        "Crunching the data...",
                        "Connecting the dots...",
                        "Drafting the report...",
                        "Double checking facts...",
                        "Saving the magic...",
                        "Almost there..."
                      ][Math.min(stageIndex, 7)]}
                    </motion.span>
                  </AnimatePresence>
                </h2>
                <p className="text-gray-600 text-xl font-medium max-w-2xl mx-auto italic mt-2">"{topic}"</p>
              </div>
              
              <ScrapbookCard className="w-full p-8 md:p-12" rotation={1}>
                <PipelineVisualizer currentStageIndex={stageIndex} />
              </ScrapbookCard>
              
              <button 
                onClick={reset}
                className="mt-10 font-bold text-gray-500 hover:text-red-500 transition-colors border-b-2 border-transparent hover:border-red-500"
              >
                Nevermind, cancel this
              </button>
            </motion.div>
          )}

          {/* ERROR STATE */}
          {appState === "ERROR" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-2xl z-10"
            >
              <ScrapbookCard className={`p-8 border-4 ${errorMsg.includes('Rate Limit Exceeded') ? 'border-[#ffb84d]' : 'border-red-500'}`} rotation={-2}>
                <div className="flex items-center space-x-4 mb-6">
                  <AlertTriangle className={`w-10 h-10 ${errorMsg.includes('Rate Limit Exceeded') ? 'text-[#ffb84d]' : 'text-red-500'}`} />
                  <h2 className="text-3xl font-heading font-bold text-gray-900">
                    {errorMsg.includes('Rate Limit Exceeded') ? 'Whoa, slow down!' : 'Oops! Something broke.'}
                  </h2>
                </div>
                <p className="text-gray-800 mb-8 font-mono bg-gray-100 p-6 rounded-xl border border-gray-200 text-sm leading-relaxed">
                  {errorMsg}
                </p>
                <button
                  onClick={reset}
                  className="bg-gray-900 hover:bg-gray-800 text-white font-bold px-8 py-3 rounded-full transition-colors w-full sm:w-auto"
                >
                  Let's try that again
                </button>
              </ScrapbookCard>
            </motion.div>
          )}

          {/* RESULTS STATE */}
          {appState === "RESULTS" && jobData?.result && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-5xl z-10"
              ref={resultsRef}
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between mb-12 gap-6">
                <div className="max-w-3xl">
                  <h1 className="text-4xl md:text-5xl font-heading font-bold text-gray-900 leading-tight mb-4">{topic}</h1>
                  <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 font-bold">
                    <span className="bg-gray-200 px-3 py-1 rounded-full uppercase tracking-wider">{style}</span>
                    <span>•</span>
                    <span>{new Date(jobData.updated_at).toLocaleTimeString()}</span>
                    {!skipMemory && jobData.result.memory_context && (
                      <>
                        <span>•</span>
                        <span className="text-[#ff90e8] flex items-center bg-pink-50 px-3 py-1 rounded-full"><CheckCircle2 className="w-4 h-4 mr-1" /> Remembered Context</span>
                      </>
                    )}
                  </div>
                </div>
                <button 
                  onClick={reset} 
                  className="shrink-0 flex items-center justify-center space-x-2 bg-white border-2 border-gray-900 hover:bg-gray-50 text-gray-900 px-6 py-3 rounded-full font-bold transition-colors shadow-[2px_2px_0px_0px_rgba(26,26,26,1)] hover:shadow-[4px_4px_0px_0px_rgba(26,26,26,1)] hover:-translate-y-0.5"
                >
                  <Search className="w-5 h-5" />
                  <span>Start Fresh</span>
                </button>
              </div>

              {/* STATS ROW */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
                {[
                  { label: "Confidence", val: `${Math.round((jobData.result.fact_checked_report ? JSON.parse(jobData.result.fact_checked_report).trust_score : 0) * 100)}%`, color: 'text-[#b9ff66]', bg: 'bg-gray-900', rot: -1 },
                  { label: "Sources", val: jobData.result.sources?.length || 0, rot: 1 },
                  { label: "Verified", val: jobData.result.claims?.filter((c:any) => c.status === "verified").length || 0, rot: 0 },
                  { label: "Unverified", val: jobData.result.claims?.filter((c:any) => c.status !== "verified").length || 0, color: 'text-[#ffb84d]', rot: 2 },
                ].map((stat, i) => (
                  <ScrapbookCard key={i} className={`p-6 flex flex-col justify-center ${stat.bg || 'bg-white'}`} rotation={stat.rot}>
                    <div className={`text-xs font-bold ${stat.bg ? 'text-gray-400' : 'text-gray-500'} mb-2 uppercase tracking-wider`}>{stat.label}</div>
                    <div className={`text-4xl font-heading font-black ${stat.color || (stat.bg ? 'text-white' : 'text-gray-900')}`}>
                      {stat.val}
                    </div>
                  </ScrapbookCard>
                ))}
              </div>

              {/* MAIN REPORT */}
              <ScrapbookCard className="p-8 md:p-12 mb-12" rotation={-0.5}>
                <div className="flex justify-between items-center mb-8 pb-6 border-b-2 border-gray-100">
                  <h2 className="text-3xl font-heading font-bold text-gray-900">Your Output</h2>
                  <div className="flex space-x-3">
                    <button onClick={copyReport} className="flex items-center space-x-2 px-4 py-2 text-sm font-bold bg-white border-2 border-gray-200 hover:border-gray-900 text-gray-900 rounded-lg transition-all">
                      <Copy className="w-4 h-4" />
                      <span className="hidden sm:inline">Copy</span>
                    </button>
                    <button onClick={downloadReport} className="flex items-center space-x-2 px-4 py-2 text-sm font-bold bg-[#b9ff66] border-2 border-gray-900 text-gray-900 rounded-lg transition-all hover:bg-[#a3e655] shadow-[2px_2px_0px_0px_rgba(26,26,26,1)] hover:shadow-[3px_3px_0px_0px_rgba(26,26,26,1)] hover:-translate-y-0.5">
                      <Download className="w-4 h-4" />
                      <span className="hidden sm:inline">Export</span>
                    </button>
                  </div>
                </div>
                <div className="text-lg text-gray-800 prose prose-lg max-w-none">
                  <ReportRenderer content={jobData.result.report || "No report generated."} />
                </div>
              </ScrapbookCard>

              {/* TABS */}
              <div className="mb-20">
                <h3 className="text-2xl font-heading font-bold text-gray-900 mb-6 ml-2">Behind the scenes</h3>
                <TabSystem 
                  claims={jobData.result.claims || []}
                  analysis={jobData.result.analysis || ""}
                  sources={jobData.result.sources || []}
                />
              </div>

            </motion.div>
          )}

        </AnimatePresence>
      </main>
    </div>
  );
}
