"use client";

import React from "react";
import ReactMarkdown from "react-markdown";

interface ReportRendererProps {
  content: string;
}

export function ReportRenderer({ content }: ReportRendererProps) {
  return (
    <div className="prose max-w-none 
      prose-headings:font-heading prose-headings:font-bold prose-headings:text-gray-900
      prose-p:text-gray-800 prose-p:leading-relaxed
      prose-a:text-[#ff90e8] prose-a:underline hover:prose-a:text-[#ff90e8]
      prose-strong:text-gray-900 prose-strong:font-bold
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
