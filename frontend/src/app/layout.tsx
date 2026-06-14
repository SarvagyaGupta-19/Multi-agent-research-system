import type { Metadata } from "next";
import { Space_Grotesk, Outfit } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-heading",
  subsets: ["latin"],
});

const outfit = Outfit({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Multi Agent Research AI",
  description: "Autonomous 4-agent research pipeline.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${outfit.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-black text-slate-100 selection:bg-cyan-900 selection:text-cyan-50 relative overflow-x-hidden">
        {/* Background Image */}
        <div 
          className="fixed inset-0 z-[-3] bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: `url('/bg-stars.jpg')` }}
        />
        
        {/* Subtle Gradient Overlay so stars remain bright but bottom has contrast */}
        <div className="fixed inset-0 z-[-2] bg-gradient-to-b from-transparent via-black/20 to-black/80" />

        <main className="flex-1 flex flex-col w-full relative z-0 font-sans">
          {children}
        </main>
      </body>
    </html>
  );
}
