import type { Metadata } from "next";
import { Playfair_Display, Inter } from "next/font/google";
import "./globals.css";

const playfair = Playfair_Display({
  variable: "--font-heading",
  subsets: ["latin"],
});

const inter = Inter({
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
      className={`${playfair.variable} ${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[#fcfbf9] text-gray-900 selection:bg-pink-200 selection:text-gray-900 relative overflow-x-hidden font-sans">
        {/* Grid Background */}
        <div 
          className="fixed inset-0 z-[-3] graph-paper-bg"
        />

        <main className="flex-1 flex flex-col w-full relative z-0">
          {children}
        </main>
      </body>
    </html>
  );
}
