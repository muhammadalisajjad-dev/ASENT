import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

export const CAVR_FRAMES = 600;

export type CAVREvidence = {
  status: string;
  packageName: string;
  version: string;
  sha256: string;
  artifact: string;
  ecosystem: string;
  violations: number;
  runId: string | null;
  stale: boolean;
  integrityValid: boolean;
  required: string[];
  denied: string[];
};

export type Props = {
  evidence: CAVREvidence;
};

// Design System Colors matching SABLE master
const C = {
  bg: '#080d16',
  cardBg: '#0f172a',
  cardBorder: '#1e293b',
  textMuted: '#64748b',
  textSecondary: '#94a3b8',
  textPrimary: '#f8fafc',
  bluePrimary: '#60a5fa',
  blueDark: '#1e3a8a',
  blueGlow: 'rgba(59, 130, 246, 0.28)',
  cyanPrimary: '#22d3ee',
  cyanGlow: 'rgba(34, 211, 238, 0.25)',
  emeraldPrimary: '#34d399',
  emeraldDark: '#065f46',
  emeraldGlow: 'rgba(52, 211, 153, 0.3)',
  amberPrimary: '#fbbf24',
  amberDark: '#78350f',
  amberBg: '#38200d',
  redPrimary: '#f87171',
  redDark: '#7f1d1d',
  redBg: 'rgba(239, 68, 68, 0.18)',
};

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

const appear = (f: number, start: number, end: number) => interpolate(f, [start, end], [0, 1], clamp);
const fade = (f: number, start: number, end: number) => interpolate(f, [start, end], [1, 0], clamp);
const move = (f: number, a: number, b: number, start: number, end: number) =>
  interpolate(f, [start, end], [a, b], {...clamp, easing: easeInOut});

// Hero 1: Package Artifact Component (pypdf wheel/artifact)
const PackageHero: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  name?: string;
  version?: string;
  sha?: string;
}> = ({x, y, scale = 1, opacity = 1, name = 'pypdf', version = '6.19.0', sha = '7e5d6e730e7d'}) => {
  return (
    <g transform={`translate(${x}, ${y}) scale(${scale})`} opacity={opacity}>
      {/* Pedestal Glow & Shadow */}
      <ellipse cx="0" cy="115" rx="140" ry="30" fill={C.blueGlow} opacity={0.7} />
      <ellipse cx="0" cy="115" rx="110" ry="20" fill="#030712" opacity={0.8} />

      {/* Package Hexagonal / Capsule Body */}
      <path
        d="M -100 -50 L 100 -50 L 120 0 L 100 80 L -100 80 L -120 0 Z"
        fill="url(#pkgBodyGrad)"
        stroke={C.bluePrimary}
        strokeWidth="3.5"
      />

      {/* PyPI / Package Ribbon & Logo */}
      <path d="M -100 -50 L 0 -20 L 100 -50" fill="none" stroke="#93c5fd" strokeWidth="2.5" />
      <path d="M 0 -20 L 0 80" fill="none" stroke="#3b82f6" strokeWidth="2" opacity={0.6} />

      {/* Package Seal Badge */}
      <g transform="translate(0, 10)">
        <rect x="-48" y="-14" width="96" height="28" rx="14" fill="#0b1728" stroke={C.bluePrimary} strokeWidth="2" />
        <text
          x="0"
          y="5"
          fill="#eff6ff"
          fontFamily="system-ui, -apple-system, sans-serif"
          fontSize="13"
          fontWeight="800"
          letterSpacing="1"
          textAnchor="middle"
        >
          PyPI WHEEL
        </text>
      </g>

      {/* Floating Artifact Tags */}
      <g transform="translate(85, -42)">
        <rect x="-16" y="-12" width="32" height="24" rx="6" fill="#1e293b" stroke={C.cyanPrimary} strokeWidth="1.6" transform="rotate(10)" />
        <text x="0" y="4" fill={C.cyanPrimary} fontSize="10" fontWeight="800" textAnchor="middle">
          .whl
        </text>
      </g>

      {/* Labels */}
      <text
        x="0"
        y="155"
        fill={C.textPrimary}
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="26"
        fontWeight="800"
        textAnchor="middle"
      >
        {name} · {version}
      </text>
      <text
        x="0"
        y="180"
        fill={C.bluePrimary}
        fontFamily="'JetBrains Mono', monospace"
        fontSize="12"
        fontWeight="650"
        letterSpacing="0.8"
        textAnchor="middle"
        opacity={0.9}
      >
        sha256: {sha.slice(0, 12)}…
      </text>
    </g>
  );
};

// Hero 2: Isolated Runtime Sandbox Capsule
const RuntimeHero: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  activeViolations?: boolean;
}> = ({x, y, scale = 1, opacity = 1, activeViolations = false}) => {
  const borderCol = activeViolations ? C.redPrimary : C.cyanPrimary;
  const glowCol = activeViolations ? 'rgba(239, 68, 68, 0.35)' : C.cyanGlow;

  return (
    <g transform={`translate(${x}, ${y}) scale(${scale})`} opacity={opacity}>
      {/* Base glow */}
      <ellipse cx="0" cy="115" rx="160" ry="32" fill={glowCol} opacity={0.7} />
      <ellipse cx="0" cy="115" rx="130" ry="20" fill="#030712" opacity={0.8} />

      {/* Outer Sandbox Vessel */}
      <rect
        x="-140"
        y="-85"
        width="280"
        height="190"
        rx="32"
        fill="url(#runtimeBodyGrad)"
        stroke={borderCol}
        strokeWidth="3.5"
      />

      {/* Subtle Container Inner Accent */}
      <rect
        x="-128"
        y="-73"
        width="256"
        height="166"
        rx="24"
        fill="none"
        stroke="rgba(34, 211, 238, 0.12)"
        strokeWidth="1"
      />

      {/* Process Header Chip with ample space: circle and text do NOT overlap */}
      <g transform="translate(0, -62)">
        <rect x="-95" y="-14" width="190" height="28" rx="14" fill="#091b29" stroke={borderCol} strokeWidth="1.8" />
        <circle cx="-74" cy="0" r="4.5" fill={borderCol} />
        <text
          x="-58"
          y="4.5"
          fill="#f0fdfa"
          fontFamily="system-ui, -apple-system, sans-serif"
          fontSize="12"
          fontWeight="800"
          letterSpacing="1"
          textAnchor="start"
        >
          ISOLATED RUNTIME
        </text>
      </g>

      {/* Process Core / PID Dial */}
      <g transform="translate(0, 15)">
        <circle cx="0" cy="0" r="34" fill="#07202c" stroke={borderCol} strokeWidth="2.5" />
        <circle cx="0" cy="0" r="22" fill="none" stroke={borderCol} strokeWidth="1.5" strokeDasharray="4 4" />
        <circle cx="0" cy="0" r="7" fill={borderCol} opacity={0.4} />
        <text
          x="0"
          y="4"
          fill="#ffffff"
          fontFamily="'JetBrains Mono', monospace"
          fontSize="11"
          fontWeight="800"
          textAnchor="middle"
        >
          PID 204
        </text>
      </g>

      {/* Process Memory / Confined Indicator */}
      <g transform="translate(0, 72)">
        <circle cx="-24" cy="0" r="3" fill={borderCol} opacity={0.9} />
        <circle cx="-8" cy="0" r="3" fill={borderCol} opacity={0.6} />
        <circle cx="8" cy="0" r="3" fill={borderCol} opacity={0.4} />
        <circle cx="24" cy="0" r="3" fill={borderCol} opacity={0.2} />
      </g>

      {/* Bottom Labels: Placed cleanly below pedestal with ample whitespace */}
      <text
        x="0"
        y="170"
        fill={C.textPrimary}
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="24"
        fontWeight="800"
        textAnchor="middle"
      >
        InvoiceHub Process
      </text>
      <text
        x="0"
        y="196"
        fill={C.cyanPrimary}
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="12"
        fontWeight="700"
        letterSpacing="2.5"
        textAnchor="middle"
      >
        CAPABILITY CONFINED
      </text>
    </g>
  );
};

// IDE Window for CAVR
const CAVREditor: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
}> = ({x, y, scale = 1, opacity = 1}) => {
  return (
    <g transform={`translate(${x}, ${y}) scale(${scale})`} opacity={opacity}>
      <rect x="0" y="0" width="820" height="420" rx="16" fill="#0b1320" stroke="#1e293b" strokeWidth="2.5" />
      <path d="M 0 52 L 820 52" stroke="#1e293b" strokeWidth="2" />
      <circle cx="26" cy="26" r="6.5" fill="#ef4444" />
      <circle cx="48" cy="26" r="6.5" fill="#f59e0b" />
      <circle cx="70" cy="26" r="6.5" fill="#10b981" />

      {/* Tab */}
      <rect x="105" y="10" width="180" height="34" rx="8" fill="#131e33" stroke="#263852" strokeWidth="1" />
      <text x="125" y="32" fill="#cbd5e1" fontFamily="monospace" fontSize="14" fontWeight="600">
        requirements.txt
      </text>
      <text x="700" y="32" fill="#64748b" fontFamily="monospace" fontSize="13">
        PIP / PYPI
      </text>

      {/* Code with tspan */}
      <g transform="translate(25, 75)">
        <rect x="38" y="14" width="730" height="60" rx="8" fill="rgba(59, 130, 246, 0.1)" stroke="rgba(59, 130, 246, 0.35)" strokeWidth="1.2" />
        <text x="15" y="38" fontFamily="'JetBrains Mono', monospace" fontSize="15">
          <tspan fill="#64748b">01  </tspan>
          <tspan fill="#60a5fa" fontWeight="700">pypdf</tspan>
          <tspan fill="#94a3b8"> == </tspan>
          <tspan fill="#34d399" fontWeight="600">"6.19.0"</tspan>
          <tspan fill="#64748b">  # sha256: 7e5d6e730e7d…</tspan>
        </text>
        <text x="15" y="60" fontFamily="'JetBrains Mono', monospace" fontSize="13">
          <tspan fill="#64748b">02  </tspan>
          <tspan fill="#94a3b8"># Ecosystem: PyPI · Wheel distribution format</tspan>
        </text>

        <text x="15" y="106" fontFamily="'JetBrains Mono', monospace" fontSize="15">
          <tspan fill="#64748b">03  </tspan>
          <tspan fill="#c084fc" fontWeight="700">import </tspan>
          <tspan fill="#f8fafc">pypdf</tspan>
        </text>
        <text x="15" y="140" fontFamily="'JetBrains Mono', monospace" fontSize="15">
          <tspan fill="#64748b">04  </tspan>
          <tspan fill="#c084fc" fontWeight="700">def </tspan>
          <tspan fill="#fde047" fontWeight="600">extract_invoice</tspan>
          <tspan fill="#f8fafc">(file_path):</tspan>
        </text>
        <text x="15" y="174" fontFamily="'JetBrains Mono', monospace" fontSize="15">
          <tspan fill="#64748b">05    </tspan>
          <tspan fill="#f8fafc">reader = pypdf.PdfReader(file_path)</tspan>
        </text>
        <text x="15" y="208" fontFamily="'JetBrains Mono', monospace" fontSize="15">
          <tspan fill="#64748b">06    </tspan>
          <tspan fill="#c084fc" fontWeight="700">return </tspan>
          <tspan fill="#38bdf8">reader.pages[0].extract_text()</tspan>
        </text>
      </g>
    </g>
  );
};

export const CAVRFilm: React.FC<Props> = ({evidence}) => {
  const f = useCurrentFrame();

  const status = evidence.status || 'VERIFIED';
  const isVerified = status === 'VERIFIED';
  const statusColor = isVerified ? C.emeraldPrimary : C.redPrimary;

  // ----------------------------------------------------
  // Timing & Choreography (600 frames total, 30fps)
  // ----------------------------------------------------
  // 0 - 2.8s (f: 0 - 85)   : Developer IDE centered
  // 2.8 - 5.5s (f: 85 - 165): IDE moves top-left, Package materializes, enters Runtime
  // 5.5 - 8.5s (f: 165 - 255): Capability Boundary expands around Runtime
  // 8.5 - 12.0s (f: 255 - 360): Normal PDF execution through FILE_READ boundary
  // 12.0 - 15.0s (f: 360 - 450): Controlled Trigger -> Forbidden NETWORK_CONNECT blocked
  // 15.0 - 17.0s (f: 450 - 510): Causal Evidence Token & Linkage graph
  // 17.0 - 19.0s (f: 510 - 570): Bounded Assurance card unfolds
  // 19.0 - 20.0s (f: 570 - 600): Final Supported CAVR Result (VERIFIED)

  // Editor animation
  const editorScale = move(f, 1.0, 0.55, 75, 110);
  const editorX = move(f, 550, 90, 75, 110);
  const editorY = move(f, 260, 150, 75, 110);
  const editorOpacity = fade(f, 500, 520);

  // Package Artifact Animation
  const packageMaterialize = appear(f, 80, 115);
  // Package moves from x: 450 to x: 1080 (into runtime) at f: 125 to 165
  const packageX = f < 125 ? 450 : move(f, 450, 1080, 125, 165);
  const packageOpacity = f < 125 ? packageMaterialize : fade(f, 150, 170);

  // Runtime Hero Animation (Appears at 1080, 500)
  const runtimeAppear = appear(f, 100, 135);
  const runtimeX = f < 505 ? 1080 : move(f, 1080, 540, 505, 535);
  const runtimeY = 500;
  const runtimeOpacity = f < 570 ? runtimeAppear : fade(f, 570, 580);

  // Capability Boundary Shield (Fades in smoothly at f: 165 - 195, NO sweeping scale)
  const boundaryOpacity = appear(f, 165, 195);

  // PDF Document Flow Animation:
  // Compact, recognizable document token flows through the pipeline
  // Phase 1 (f: 255 - 280): Travels from workspace (x: 420) through FILE_READ node (x: 810) into runtime core (x: 1080)
  // Phase 2 (f: 280 - 325): Centered in runtime core; normal execution HUD indicators appear
  // Phase 3 (f: 325 - 355): Exits smoothly to the right (x: 1080 -> 1520) and dissolves
  const pdfX =
    f < 280
      ? move(f, 420, 1080, 255, 280)
      : f < 325
      ? 1080
      : move(f, 1080, 1520, 325, 355);
  const pdfOpacity = interpolate(f, [250, 262, 342, 355], [0, 1, 1, 0], clamp);
  const pdfActiveInCore = f >= 280 && f < 328;

  // Trigger Animation:
  // Phase 1 (f: 360 - 386): Controlled canary trigger packet arrives from left into runtime core
  // Phase 2 (f: 386 - 425): Active inside core, activates dormant package canary
  const triggerX = f < 386 ? move(f, 420, 1080, 360, 386) : 1080;
  const triggerOpacity = interpolate(f, [355, 368, 435, 450], [0, 1, 1, 0], clamp);
  const triggerActive = f >= 386 && f < 440;

  // Outbound Network Exfiltration Attempt Signal (f: 390 to 406):
  // Red probe shoots from process core (x: 1080, y: 500) directly to NETWORK_CONNECT node (x: 1350, y: 450)
  const probeProgress = interpolate(f, [390, 404], [0, 1], clamp);
  const probeActive = triggerActive && probeProgress > 0 && f < 415;
  const blockedFlash = interpolate(f, [404, 412, 442, 455], [0, 1, 1, 0], clamp);

  // Causal Evidence Token (f: 450 to 510)
  const causalTokenAppear = appear(f, 450, 475);

  // Obligations / Bounded Assurance (f: 515 to 570)
  const boundsAppear = interpolate(f, [515, 535, 565, 575], [0, 1, 1, 0], clamp);

  // Final Result Card (f: 572 to 600)
  const resultCardAppear = appear(f, 572, 585);

  return (
    <svg width="100%" height="100%" viewBox="0 0 1920 1080" style={{background: C.bg}}>
      <defs>
        {/* Gradients */}
        <radialGradient id="stageGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#1e293b" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#080d16" stopOpacity="0" />
        </radialGradient>

        <linearGradient id="pkgBodyGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#1e3a8a" />
          <stop offset="50%" stopColor="#0f172a" />
          <stop offset="100%" stopColor="#030712" />
        </linearGradient>

        <linearGradient id="runtimeBodyGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#082f49" />
          <stop offset="50%" stopColor="#0a1926" />
          <stop offset="100%" stopColor="#040b12" />
        </linearGradient>

        <filter id="glowEffect" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="8" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Background Stage */}
      <rect width="1920" height="1080" fill={C.bg} />
      <circle cx="960" cy="540" r="750" fill="url(#stageGlow)" />

      {/* Technical Grid */}
      <g opacity={0.07}>
        {Array.from({length: 17}, (_, i) => (
          <path key={'v' + i} d={`M ${120 * i} 0 L ${120 * i} 1080`} stroke="#64748b" strokeWidth="1" />
        ))}
        {Array.from({length: 10}, (_, i) => (
          <path key={'h' + i} d={`M 0 ${120 * i} L 1920 ${120 * i}`} stroke="#64748b" strokeWidth="1" />
        ))}
      </g>

      {/* Top Header Bar */}
      <g transform="translate(90, 65)">
        <text
          x="0"
          y="0"
          fill={C.bluePrimary}
          fontFamily="system-ui, -apple-system, sans-serif"
          fontSize="14"
          fontWeight="700"
          letterSpacing="2.5"
        >
          ASENT  /  SECURITY MECHANISM DEMONSTRATION
        </text>
        <text
          x="0"
          y="38"
          fill={C.textPrimary}
          fontFamily="system-ui, -apple-system, sans-serif"
          fontSize="30"
          fontWeight="800"
          letterSpacing="0.5"
        >
          CAVR · CAPABILITY ASSURANCE &amp; RUNTIME VERIFICATION
        </text>
      </g>

      {/* Controlled Local Model Tag */}
      <g transform="translate(1550, 60)">
        <rect x="0" y="0" width="280" height="34" rx="17" fill="#1e1828" stroke="#f59e0b" strokeWidth="1.5" />
        <circle cx="20" cy="17" r="4.5" fill="#f59e0b" />
        <text
          x="34"
          y="22"
          fill="#fde047"
          fontFamily="system-ui, -apple-system, sans-serif"
          fontSize="12"
          fontWeight="700"
          letterSpacing="1.2"
        >
          CONTROLLED / LOCAL MODEL
        </text>
      </g>

      {/* 1. IDE Code Editor */}
      {editorOpacity > 0 && (
        <CAVREditor x={editorX} y={editorY} scale={editorScale} opacity={editorOpacity} />
      )}

      {/* 2. Package Artifact Hero */}
      {packageOpacity > 0 && (
        <PackageHero
          x={packageX}
          y={500}
          scale={0.95}
          opacity={packageOpacity}
          name={evidence.packageName || 'pypdf'}
          version={evidence.version || '6.19.0'}
          sha={evidence.sha256 || '7e5d6e730e7d'}
        />
      )}

      {/* 3. Isolated Runtime Sandbox Hero */}
      {runtimeOpacity > 0 && (
        <RuntimeHero
          x={runtimeX}
          y={runtimeY}
          scale={1.0}
          opacity={runtimeOpacity}
          activeViolations={triggerActive}
        />
      )}

      {/* 4. Capability Boundary Perimeter & Badges (Frames 165 - 505) */}
      {/* Seamless geometric design: Perimeter is 540x270, wrapping cleanly around the vessel and pedestal */}
      {boundaryOpacity > 0 && f < 505 && (
        <g transform={`translate(${runtimeX}, ${runtimeY})`} opacity={boundaryOpacity}>
          {/* Security Confinement Perimeter Rectangle: y spans [-120, +150] */}
          <rect
            x="-270"
            y="-120"
            width="540"
            height="270"
            rx="32"
            fill="none"
            stroke="#1e3a8a"
            strokeWidth="2.2"
            strokeDasharray="9 7"
          />

          {/* Permitted: FILE_READ (Top-Left, y: -50) */}
          <g transform="translate(-270, -50)">
            <rect x="-75" y="-16" width="150" height="32" rx="16" fill="#062e24" stroke={C.emeraldPrimary} strokeWidth="2" />
            <circle cx="-55" cy="0" r="4" fill={C.emeraldPrimary} />
            <text x="4" y="4.5" fill={C.emeraldPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="12" fontWeight="800" textAnchor="middle">
              FILE_READ ✓
            </text>
          </g>

          {/* Permitted: FILE_WRITE (Bottom-Left, y: 50 - completely above InvoiceHub text) */}
          <g transform="translate(-270, 50)">
            <rect x="-75" y="-16" width="150" height="32" rx="16" fill="#062e24" stroke={C.emeraldPrimary} strokeWidth="2" />
            <circle cx="-55" cy="0" r="4" fill={C.emeraldPrimary} />
            <text x="4" y="4.5" fill={C.emeraldPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="12" fontWeight="800" textAnchor="middle">
              FILE_WRITE ✓
            </text>
          </g>

          {/* Denied: NETWORK_CONNECT (Top-Right, y: -50) */}
          <g transform="translate(270, -50)">
            <rect
              x="-90"
              y="-16"
              width="180"
              height="32"
              rx="16"
              fill={blockedFlash > 0.3 ? '#5b0f0f' : C.redBg}
              stroke={C.redPrimary}
              strokeWidth={blockedFlash > 0.3 ? '3' : '2'}
            />
            <circle cx="-68" cy="0" r="4.5" fill={C.redPrimary} />
            <text x="8" y="4.5" fill={C.redPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="12" fontWeight="800" textAnchor="middle">
              NETWORK 🚫 DENIED
            </text>
          </g>

          {/* Denied: PROCESS_CREATE (Bottom-Right, y: 50 - completely above InvoiceHub text) */}
          <g transform="translate(270, 50)">
            <rect x="-90" y="-16" width="180" height="32" rx="16" fill={C.redBg} stroke={C.redPrimary} strokeWidth="2" />
            <circle cx="-68" cy="0" r="4.5" fill={C.redPrimary} />
            <text x="8" y="4.5" fill={C.redPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="12" fontWeight="800" textAnchor="middle">
              PROCESS 🚫 DENIED
            </text>
          </g>
        </g>
      )}

      {/* 5. Normal Execution: PDF Document Flow Through Process (Frames 255 - 355) */}
      {/* Sized appropriately (54x68) so it fits elegantly within the core and never occludes chips */}
      {pdfOpacity > 0 && (
        <g transform={`translate(${pdfX}, 500)`} opacity={pdfOpacity}>
          <rect x="-27" y="-34" width="54" height="68" rx="8" fill="#0b1726" stroke={C.emeraldPrimary} strokeWidth="2" />
          <path d="M 9 -34 L 27 -16 L 9 -16 Z" fill="#1e293b" />
          <text x="0" y="-5" fill={C.emeraldPrimary} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="900" textAnchor="middle">
            PDF
          </text>
          <text x="0" y="14" fill="#94a3b8" fontFamily="'JetBrains Mono', monospace" fontSize="9" fontWeight="700" textAnchor="middle">
            invoice
          </text>
          <circle cx="0" cy="24" r="2.5" fill={C.emeraldPrimary} />
        </g>
      )}

      {/* Normal Execution Output HUD: Appears cleanly above container (y: 330) during extraction */}
      {pdfActiveInCore && (
        <g
          transform="translate(1080, 330)"
          opacity={interpolate(f, [280, 290, 320, 328], [0, 1, 1, 0], clamp)}
        >
          <rect x="-185" y="-18" width="370" height="36" rx="18" fill="#062e24" stroke={C.emeraldPrimary} strokeWidth="1.8" />
          <circle cx="-160" cy="0" r="4.5" fill={C.emeraldPrimary} />
          <text x="10" y="4.5" fill="#a7f3d0" fontFamily="'JetBrains Mono', monospace" fontSize="12" fontWeight="700" textAnchor="middle">
            EXTRACTED: INVOICE #1042 · $12,450.00
          </text>
        </g>
      )}

      {/* 6. Controlled Canary Trigger & Forbidden Capability Attempt (Frames 360 - 455) */}
      {/* Arrives at y: 500 (core height), avoiding collision with top chip */}
      {triggerOpacity > 0 && (
        <g transform={`translate(${triggerX}, 500)`} opacity={triggerOpacity}>
          <rect x="-85" y="-22" width="170" height="44" rx="14" fill="#38200d" stroke={C.amberPrimary} strokeWidth="2.2" />
          <circle cx="-62" cy="0" r="4.5" fill={C.amberPrimary} />
          <text x="10" y="-2" fill={C.amberPrimary} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="800" textAnchor="middle">
            CONTROLLED TRIGGER
          </text>
          <text x="10" y="13" fill="#fef08a" fontFamily="'JetBrains Mono', monospace" fontSize="11" fontWeight="700" textAnchor="middle">
            canary_eval()
          </text>
        </g>
      )}

      {/* Forbidden Network Exfiltration Probe Signal (Frames 390 - 415) */}
      {probeActive && (
        <g opacity={interpolate(f, [390, 395, 408, 415], [0, 1, 1, 0], clamp)}>
          <line
            x1="1080"
            y1="500"
            x2={1080 + (1350 - 1080) * probeProgress}
            y2={500 + (450 - 500) * probeProgress}
            stroke={C.redPrimary}
            strokeWidth="3.5"
            strokeDasharray="6 4"
          />
          <circle
            cx={1080 + (1350 - 1080) * probeProgress}
            cy={500 + (450 - 500) * probeProgress}
            r="6.5"
            fill={C.redPrimary}
          />
        </g>
      )}

      {/* Intercept Alert Card: Placed to the right of the NETWORK_CONNECT boundary node at (1520, 450) */}
      {blockedFlash > 0 && (
        <g transform="translate(1520, 450)" opacity={blockedFlash}>
          <rect x="-140" y="-34" width="280" height="68" rx="18" fill="#450a0a" stroke={C.redPrimary} strokeWidth="2.5" filter="url(#glowEffect)" />
          <rect x="-140" y="-34" width="280" height="68" rx="18" fill="#2d0606" stroke={C.redPrimary} strokeWidth="2" />
          <g transform="translate(0, -8)">
            <circle cx="-100" cy="0" r="5" fill={C.redPrimary} />
            <text x="10" y="4.5" fill="#fecaca" fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="900" letterSpacing="0.8" textAnchor="middle">
              INTERCEPTED &amp; BLOCKED
            </text>
          </g>
          <text x="0" y="20" fill="#f87171" fontFamily="'JetBrains Mono', monospace" fontSize="11" fontWeight="700" textAnchor="middle">
            UNAUTHORIZED NETWORK_CONNECT
          </text>
        </g>
      )}

      {/* Causal Linkage Curve (connecting trigger at core -> blocked event at boundary, f: 410 - 455) */}
      {blockedFlash > 0 && f >= 410 && (
        <g opacity={interpolate(f, [410, 420, 445, 455], [0, 0.9, 0.9, 0], clamp)}>
          <path
            d="M 1080 470 Q 1300 290 1520 410"
            fill="none"
            stroke={C.amberPrimary}
            strokeWidth="2.5"
            strokeDasharray="6 6"
          />
          <g transform="translate(1300, 310)">
            <rect x="-65" y="-12" width="130" height="24" rx="12" fill="#291807" stroke={C.amberPrimary} strokeWidth="1.2" />
            <text x="0" y="4" fill="#fde047" fontFamily="system-ui, sans-serif" fontSize="10" fontWeight="800" textAnchor="middle">
              CAUSAL LINKAGE
            </text>
          </g>
        </g>
      )}

      {/* 7. Causal Evidence Token & Linkage (Frames 450 - 510) */}
      {causalTokenAppear > 0 && f < 510 && (
        <g transform="translate(1080, 290)" opacity={causalTokenAppear}>
          <rect x="-225" y="-22" width="450" height="44" rx="22" fill="#082333" stroke={C.cyanPrimary} strokeWidth="2.2" />
          <circle cx="-190" cy="0" r="12" fill={C.cyanPrimary} />
          <text x="-190" y="4.5" fill="#042f2e" fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="900" textAnchor="middle">
            ✓
          </text>
          <text x="15" y="5.5" fill={C.cyanPrimary} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="800" letterSpacing="1.2" textAnchor="middle">
            CAUSAL EVIDENCE TOKEN CAPTURED
          </text>
        </g>
      )}

      {/* 8. Bounded Assurance & Obligations (Frames 515 - 570) */}
      {boundsAppear > 0 && (
        <g transform="translate(860, 290)" opacity={boundsAppear}>
          <rect x="0" y="0" width="840" height="420" rx="24" fill="#0b1424" stroke="#334155" strokeWidth="2.5" />
          <g transform="translate(45, 52)">
            <text x="0" y="0" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="24" fontWeight="800">
              CAVR CAPABILITY ASSURANCE BOUNDS
            </text>
            <text x="0" y="28" fill={C.textSecondary} fontFamily="system-ui, sans-serif" fontSize="14">
              Residual uncertainty and boundary verification for dependency slice
            </text>
          </g>

          {[
            {label: 'Static Capability Contract', status: 'VERIFIED', col: C.emeraldPrimary, bg: '#062e24'},
            {label: 'Dynamic Sandbox Confinement', status: 'VERIFIED', col: C.emeraldPrimary, bg: '#062e24'},
            {label: 'Bytecode Slice Coverage', status: 'BOUNDED', col: C.amberPrimary, bg: C.amberBg},
          ].map((item, idx) => (
            <g key={item.label} transform={`translate(45, ${142 + idx * 66})`}>
              <line x1="0" y1="-8" x2="750" y2="-8" stroke="#1e293b" strokeWidth="1" />
              <text x="0" y="24" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="17" fontWeight="600">
                {item.label}
              </text>
              <g transform="translate(600, 2)">
                <rect x="0" y="0" width="140" height="34" rx="17" fill={item.bg} stroke={item.col} strokeWidth="1.8" />
                <circle cx="22" cy="17" r="4.5" fill={item.col} />
                <text x="75" y="22" fill={item.col} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="800" textAnchor="middle">
                  {item.status}
                </text>
              </g>
            </g>
          ))}

          <g transform="translate(45, 356)">
            <rect x="0" y="0" width="750" height="34" rx="8" fill="#1e1828" stroke="#78350f" strokeWidth="1" />
            <text x="375" y="22" fill={C.amberPrimary} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="700" letterSpacing="0.8" textAnchor="middle">
              CONTROLLED CANARY MODEL · CAPABILITY ASSURANCE BOUNDED TO EVALUATED ARTIFACT
            </text>
          </g>
        </g>
      )}

      {/* 9. Final Supported CAVR Result (Frames 572 - 600) */}
      {resultCardAppear > 0 && (
        <g transform="translate(360, 220)" opacity={resultCardAppear}>
          <rect x="0" y="0" width="1200" height="580" rx="32" fill="#0b1322" stroke={statusColor} strokeWidth="3.5" filter="url(#glowEffect)" />
          <rect x="0" y="0" width="1200" height="580" rx="32" fill="#09111e" stroke={statusColor} strokeWidth="2.5" />

          {/* Eyebrow */}
          <g transform="translate(600, 70)">
            <rect x="-190" y="-17" width="380" height="34" rx="17" fill="#131e33" stroke={C.bluePrimary} strokeWidth="1.8" />
            <text x="0" y="5" fill="#bfdbfe" fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="800" letterSpacing="1.5" textAnchor="middle">
              SUPPORTED CAVR MECHANISM
            </text>
          </g>

          <text x="600" y="155" fill={C.textSecondary} fontFamily="system-ui, sans-serif" fontSize="26" fontWeight="600" textAnchor="middle">
            CAPABILITY ASSURANCE
          </text>

          {/* Result Banner */}
          <g transform="translate(600, 245)">
            <rect x="-260" y="-48" width="520" height="96" rx="26" fill="#062e24" stroke={statusColor} strokeWidth="3.5" />
            <text x="0" y="18" fill={statusColor} fontFamily="system-ui, sans-serif" fontSize="56" fontWeight="900" letterSpacing="2.5" textAnchor="middle">
              {status}
            </text>
          </g>

          {/* Evidence Details */}
          <g transform="translate(180, 370)">
            <line x1="0" y1="0" x2="840" y2="0" stroke="#1e293b" strokeWidth="1.5" />

            <g transform="translate(0, 42)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="600">
                EVALUATED ARTIFACT
              </text>
              <text x="0" y="28" fill={C.textPrimary} fontFamily="monospace" fontSize="17" fontWeight="700">
                {evidence.packageName || 'pypdf'} {evidence.version || '6.19.0'} · {evidence.ecosystem || 'PyPI'}
              </text>
            </g>

            <g transform="translate(480, 42)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="600">
                EVIDENCE RUN IDENTIFIER
              </text>
              <text x="0" y="28" fill={C.textPrimary} fontFamily="monospace" fontSize="17" fontWeight="700">
                {evidence.runId || 'c6f6239d62b4'} · Integrity Valid
              </text>
            </g>
          </g>

          <text x="600" y="525" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="14" fontWeight="500" textAnchor="middle">
            Controlled local model · Stored ASENT evidence checked · No live external execution claimed
          </text>
        </g>
      )}

      {/* Bottom Progress Bar */}
      <g transform="translate(90, 1020)">
        <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="500">
          LOCAL CONTROLLED VISUALIZATION · STORED EVIDENCE IS AUTHORITATIVE
        </text>
        <rect x="0" y="16" width="1740" height="4" rx="2" fill="#1e293b" />
        <rect x="0" y="16" width={(1740 * f) / CAVR_FRAMES} height="4" rx="2" fill={C.bluePrimary} />
      </g>
    </svg>
  );
};
