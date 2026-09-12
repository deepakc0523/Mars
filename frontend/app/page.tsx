import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "MARS — Incident Response Console",
};

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-24">
      {/* Hero */}
      <div className="text-center space-y-6 max-w-3xl">
        {/* Status badge */}
        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-white/60">
          <span className="h-2 w-2 rounded-full bg-mars-500 animate-pulse-slow" />
          Foundation phase · v0.1.0
        </div>

        {/* Logo / wordmark */}
        <h1 className="text-6xl font-bold tracking-tight text-white sm:text-7xl">
          <span className="text-mars-500">M</span>ARS
        </h1>

        <p className="text-xl text-white/60 font-medium">
          Multi-Agent Reasoning &amp; Adaptive Response System
        </p>

        <p className="text-base text-white/40 max-w-xl mx-auto leading-relaxed">
          A real-time incident-response agent that maintains a continuously
          updated world state, handles interruptions, re-evaluates plans, and
          drives autonomous resolution — safely.
        </p>

        {/* IPRRV loop */}
        <div className="mt-8 flex flex-wrap justify-center gap-2 text-xs font-mono font-semibold">
          {[
            "INTERRUPT",
            "PRESERVE",
            "RE-EVALUATE",
            "REPLAN",
            "VERIFY",
            "SAFETY",
            "EXECUTE",
          ].map((phase, i, arr) => (
            <span key={phase} className="flex items-center gap-2">
              <span className="rounded bg-white/5 border border-white/10 px-3 py-1.5 text-white/70 hover:border-mars-500/50 hover:text-mars-400 transition-colors">
                {phase}
              </span>
              {i < arr.length - 1 && (
                <span className="text-white/20">→</span>
              )}
            </span>
          ))}
        </div>

        {/* Quick links */}
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-white/10 bg-white/5 px-5 py-2.5 text-sm text-white/70 hover:border-mars-500/50 hover:text-mars-400 hover:bg-mars-500/5 transition-all"
          >
            API Docs →
          </a>
          <a
            href="http://localhost:8000/health"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-white/10 bg-white/5 px-5 py-2.5 text-sm text-white/70 hover:border-mars-500/50 hover:text-mars-400 hover:bg-mars-500/5 transition-all"
          >
            Health Check →
          </a>
        </div>
      </div>

      {/* Footer */}
      <footer className="absolute bottom-6 text-xs text-white/20 font-mono">
        MARS · Hackathon Project · Interruptible Real-time Agents
      </footer>
    </main>
  );
}
