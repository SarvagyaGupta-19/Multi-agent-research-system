"use client";

import React from "react";
import ReactMarkdown from "react-markdown";

interface ReportRendererProps {
  content: string;
}

export function ReportRenderer({ content }: ReportRendererProps) {
  return (
    <div className="prose prose-invert prose-slate max-w-none 
      prose-headings:font-sans prose-headings:font-bold prose-headings:text-slate-100
      prose-p:text-slate-300 prose-p:leading-relaxed
      prose-a:text-cyan-400 prose-a:no-underline hover:prose-a:underline
      prose-code:text-emerald-300 prose-code:bg-slate-800/50 prose-code:px-1 prose-code:rounded
      prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-800
      prose-blockquote:border-l-cyan-500 prose-blockquote:bg-slate-900/30 prose-blockquote:px-4 prose-blockquote:py-1
      marker:text-cyan-500
    ">
      <ReactMarkdown
        components={{
          sup: ({node, ...props}) => <sup className="text-cyan-400 font-mono" {...props} />,
          // Auto-convert standard [1] citations to superscripts if possible, 
          // but we'll rely on the markdown providing actual <sup> tags or just styling links well.
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
