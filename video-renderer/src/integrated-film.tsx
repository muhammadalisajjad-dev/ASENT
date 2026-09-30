import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

export const INTEGRATED_FRAMES = 450; // 15 seconds at 30 fps

export type IntegratedEvidence = {
  runId: string | null;
  finalDecision: string;
  reasons: string[];
  applicable: string[];
  modules: {
    CAVR: { status: string; stale: boolean; integrityValid: boolean };
    SATRA: { status: string; stale: boolean; integrityValid: boolean };
    SABLE: { status: string; stale: boolean; integrityValid: boolean };
  };
};

export type Props = {
  evidence: IntegratedEvidence;
};

// Design System Colors matching SABLE, CAVR, and SATRA masters
const C = {
  bg: '#080d16',
  cardBg: '#0f172a',
  cardBorder: '#1e293b',
  textMuted: '#64748b',
  textSecondary: '#94a3b8',
  textPrimary: '#f8fafc',
  amberPrimary: '#fbbf24',
  amberDark: '#78350f',
  amberBg: '#38200d',
  amberGlow: 'rgba(251, 191, 36, 0.28)',
  cyanPrimary: '#22d3ee',
  cyanGlow: 'rgba(34, 211, 238, 0.25)',
  emeraldPrimary: '#34d399',
  emeraldDark: '#065f46',
  emeraldGlow: 'rgba(52, 211, 153, 0.3)',
  violetPrimary: '#818cf8',
  violetDark: '#312e81',
  violetGlow: 'rgba(99, 102, 241, 0.28)',
  bluePrimary: '#60a5fa',
  blueGlow: 'rgba(96, 165, 250, 0.25)',
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

// Origin Module Node on the Left Stage
const ModuleSourceNode: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  name: string;
  sublabel: string;
  status: string;
  color: string;
  badgeBg: string;
  iconLetter: string;
}> = ({x, y, scale = 1, opacity = 1, name, sublabel, status, color, badgeBg, iconLetter}) => {
  return (
    <g transform={`translate(${x}, ${y}) scale(${scale})`} opacity={opacity}>
      <rect x="-190" y="-55" width="380" height="110" rx="20" fill="#0b1320" stroke="#1e293b" strokeWidth="2.5" />

      {/* Module Icon Emblem */}
      <g transform="translate(-135, 0)">
        <circle cx="0" cy="0" r="28" fill="#07101e" stroke={color} strokeWidth="2" />
        <text
          x="0"
          y="7"
          fill={color}
          fontFamily="system-ui, -apple-system, sans-serif"
          fontSize="17"
          fontWeight="900"
          textAnchor="middle"
        >
          {iconLetter}
        </text>
      </g>

      {/* Module Title & Scope */}
      <g transform="translate(-92, -10)">
        <text x="0" y="0" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="19" fontWeight="800">
          {name}
        </text>
        <text x="0" y="24" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="600">
          {sublabel}
        </text>
      </g>

      {/* Outcome Status Chip */}
      <g transform="translate(108, 0)">
        <rect x="-62" y="-15" width="124" height="30" rx="15" fill={badgeBg} stroke={color} strokeWidth="1.8" />
        <circle cx="-42" cy="0" r="4" fill={color} />
        <text x="8" y="4.5" fill={color} fontFamily="system-ui, sans-serif" fontSize="10.5" fontWeight="800" textAnchor="middle">
          {status}
        </text>
      </g>
    </g>
  );
};

// Converging Evidence Token Component
const EvidenceToken: React.FC<{
  x: number;
  y: number;
  opacity?: number;
  label: string;
  sub: string;
  color: string;
  icon: string;
}> = ({x, y, opacity = 1, label, sub, color, icon}) => {
  return (
    <g transform={`translate(${x}, ${y})`} opacity={opacity}>
      <rect x="-120" y="-22" width="240" height="44" rx="22" fill="#0d1829" stroke={color} strokeWidth="2" filter="url(#glowEffect)" />
      <rect x="-120" y="-22" width="240" height="44" rx="22" fill="#09111c" stroke={color} strokeWidth="1.8" />
      <circle cx="-90" cy="0" r="11" fill={color} />
      <text x="-90" y="4.5" fill="#030712" fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="900" textAnchor="middle">
        {icon}
      </text>
      <text x="12" y="-2" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="800" textAnchor="middle">
        {label}
      </text>
      <text x="12" y="13" fill={color} fontFamily="'JetBrains Mono', monospace" fontSize="9.5" fontWeight="700" textAnchor="middle">
        {sub}
      </text>
    </g>
  );
};

export const IntegratedFilm: React.FC<Props> = ({evidence}) => {
  const f = useCurrentFrame();

  const finalDecision = evidence.finalDecision || 'REVIEW';
  const isAccepted = finalDecision === 'ACCEPT' || finalDecision === 'PASS';
  const decisionColor = isAccepted ? C.emeraldPrimary : C.amberPrimary;
  const decisionBg = isAccepted ? '#062e24' : C.amberBg;

  // ----------------------------------------------------
  // Timing & Continuous Choreography (450 frames total, 30fps = 15.0s)
  // ----------------------------------------------------
  // 0 - 3.0s (f: 0 - 90)    : 3 Origin Module Nodes appear on left
  // 3.0 - 7.5s (f: 90 - 225) : 3 Evidence Tokens materialize & travel along converging routed bezier curves
  // 7.5 - 11.2s (f: 225 - 335): Tokens enter central ASENT Trust Gate; slot inspection & policy check
  // 11.2 - 13.5s (f: 335 - 405): Gate fades out; Policy Conjunction Matrix card unfolds centered
  // 13.5 - 15.0s (f: 405 - 450): Final Supported ASENT Integrated Result card (REVIEW)

  // Origin Module Nodes (f: 0 - 340)
  const modulesAppear = appear(f, 0, 30);
  const modulesOpacity = fade(f, 330, 350);

  // Evidence Tokens Travel Animation (f: 90 - 225)
  const tCavr = interpolate(f, [90, 215], [0, 1], clamp);
  const cavrTokenX = interpolate(tCavr, [0, 1], [320, 1060], clamp);
  const cavrTokenY = interpolate(tCavr, [0, 0.5, 1], [280, 370, 480], clamp);
  const cavrTokenOpacity = interpolate(f, [90, 105, 225, 235], [0, 1, 1, 0], clamp);

  const tSatra = interpolate(f, [90, 215], [0, 1], clamp);
  const satraTokenX = interpolate(tSatra, [0, 1], [320, 1060], clamp);
  const satraTokenY = 520;
  const satraTokenOpacity = interpolate(f, [90, 105, 225, 235], [0, 1, 1, 0], clamp);

  const tSable = interpolate(f, [90, 215], [0, 1], clamp);
  const sableTokenX = interpolate(tSable, [0, 1], [320, 1060], clamp);
  const sableTokenY = interpolate(tSable, [0, 0.5, 1], [760, 670, 560], clamp);
  const sableTokenOpacity = interpolate(f, [90, 105, 225, 235], [0, 1, 1, 0], clamp);

  // Central Trust Gate Hero (f: 60 - 340)
  const gateAppear = appear(f, 60, 95);
  const gateOpacity = fade(f, 335, 350);

  // Trust Gate Slots Verification States
  const slot1Verified = f >= 220; // Cryptographic Integrity
  const slot2Verified = f >= 250; // Freshness & Applicability
  const slot3Verified = f >= 280; // Bounded Policy Decision

  // Summary Inspection Card (f: 340 - 405) - Centered at x: 560
  const summaryAppear = interpolate(f, [340, 355, 395, 405], [0, 1, 1, 0], clamp);

  // Final Supported ASENT Result Card (f: 405 - 450)
  const resultCardAppear = appear(f, 405, 418);

  return (
    <svg width="100%" height="100%" viewBox="0 0 1920 1080" style={{background: C.bg}}>
      <defs>
        <radialGradient id="stageGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#1e1b4b" stopOpacity="0.45" />
          <stop offset="100%" stopColor="#080d16" stopOpacity="0" />
        </radialGradient>

        <linearGradient id="gateGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#111c30" />
          <stop offset="50%" stopColor="#0a1220" />
          <stop offset="100%" stopColor="#050811" />
        </linearGradient>

        <filter id="glowEffect" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="8" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Stage Background */}
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

      {/* Header Bar */}
      <g transform="translate(90, 65)">
        <text
          x="0"
          y="0"
          fill={C.cyanPrimary}
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
          INTEGRATED · MULTI-MODULE TRUST GATE EVALUATION
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

      {/* Converging Guide Pathways */}
      {gateAppear > 0 && f < 335 && (
        <g opacity={gateAppear * 0.35}>
          {/* Top route (CAVR to Gate) */}
          <path d="M 320 280 C 650 280, 850 480, 1100 480" fill="none" stroke={C.bluePrimary} strokeWidth="2" strokeDasharray="6 6" />
          {/* Middle route (SATRA to Gate) */}
          <path d="M 320 520 L 1100 520" fill="none" stroke={C.amberPrimary} strokeWidth="2" strokeDasharray="6 6" />
          {/* Bottom route (SABLE to Gate) */}
          <path d="M 320 760 C 650 760, 850 560, 1100 560" fill="none" stroke={C.violetPrimary} strokeWidth="2" strokeDasharray="6 6" />
        </g>
      )}

      {/* 1. Origin Module Nodes on the Left (f: 0 - 340) */}
      {modulesOpacity > 0 && (
        <g opacity={modulesOpacity * modulesAppear}>
          {/* CAVR Origin Node */}
          <ModuleSourceNode
            x={320}
            y={280}
            name="CAVR"
            sublabel="Dependency Slice"
            status={evidence.modules.CAVR.status || 'VERIFIED'}
            color={C.emeraldPrimary}
            badgeBg="#062e24"
            iconLetter="C"
          />

          {/* SATRA-RV Origin Node */}
          <ModuleSourceNode
            x={320}
            y={520}
            name="SATRA-RV"
            sublabel="Application Code"
            status={evidence.modules.SATRA.status || 'INCONCLUSIVE'}
            color={C.amberPrimary}
            badgeBg={C.amberBg}
            iconLetter="S"
          />

          {/* SABLE Origin Node */}
          <ModuleSourceNode
            x={320}
            y={760}
            name="SABLE"
            sublabel="Infrastructure Slice"
            status={evidence.modules.SABLE.status || 'PRESERVED'}
            color={C.emeraldPrimary}
            badgeBg="#062e24"
            iconLetter="S"
          />
        </g>
      )}

      {/* 2. Converging Evidence Tokens (f: 90 - 235) */}
      {cavrTokenOpacity > 0 && (
        <EvidenceToken
          x={cavrTokenX}
          y={cavrTokenY}
          opacity={cavrTokenOpacity}
          label="CAVR EVIDENCE"
          sub="sha256:7e5d6e · VERIFIED"
          color={C.emeraldPrimary}
          icon="✓"
        />
      )}

      {satraTokenOpacity > 0 && (
        <EvidenceToken
          x={satraTokenX}
          y={satraTokenY}
          opacity={satraTokenOpacity}
          label="SATRA EVIDENCE"
          sub="IDOR.001 · INCONCLUSIVE"
          color={C.amberPrimary}
          icon="!"
        />
      )}

      {sableTokenOpacity > 0 && (
        <EvidenceToken
          x={sableTokenX}
          y={sableTokenY}
          opacity={sableTokenOpacity}
          label="SABLE EVIDENCE"
          sub="s3_data · PRESERVED"
          color={C.emeraldPrimary}
          icon="✓"
        />
      )}

      {/* 3. ASENT Trust Gate Hero Vessel (f: 60 - 350) */}
      {gateOpacity > 0 && (
        <g transform="translate(1320, 520)" opacity={gateAppear * gateOpacity}>
          {/* Base Pedestal Glow */}
          <ellipse cx="0" cy="275" rx="300" ry="40" fill={C.cyanGlow} opacity={0.65} />
          <ellipse cx="0" cy="275" rx="240" ry="24" fill="#030712" opacity={0.8} />

          {/* Gate Outer Monolith Chassis */}
          <rect
            x="-280"
            y="-250"
            width="560"
            height="500"
            rx="32"
            fill="url(#gateGrad)"
            stroke={decisionColor}
            strokeWidth="3.5"
          />
          <rect
            x="-264"
            y="-234"
            width="528"
            height="468"
            rx="24"
            fill="none"
            stroke="rgba(34, 211, 238, 0.15)"
            strokeWidth="1.2"
          />

          {/* Header Emblem */}
          <g transform="translate(0, -215)">
            <rect x="-140" y="-16" width="280" height="32" rx="16" fill="#072033" stroke={C.cyanPrimary} strokeWidth="1.8" />
            <circle cx="-115" cy="0" r="4.5" fill={C.cyanPrimary} />
            <text x="12" y="4.5" fill="#a5f3fc" fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="800" letterSpacing="1.2" textAnchor="middle">
              ASENT TRUST GATE
            </text>
          </g>

          {/* Subtitle */}
          <text x="0" y="-160" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="24" fontWeight="800" textAnchor="middle">
            Multi-Evidence Convergence
          </text>
          <text x="0" y="-136" fill={C.textMuted} fontFamily="'JetBrains Mono', monospace" fontSize="11" fontWeight="600" textAnchor="middle">
            Run ID: {evidence.runId || 'c6f6239d62b4'} · Automated Policy Gate
          </text>

          {/* Three Gate Slot Inspection Rows */}
          {[
            {
              slot: '01',
              title: 'Cryptographic Hash Digests',
              state: slot1Verified ? 'VALID (3/3 VERIFIED)' : 'VERIFYING…',
              col: C.emeraldPrimary,
              bg: '#062e24',
              icon: '✓',
            },
            {
              slot: '02',
              title: 'Evidence Freshness & Applicability',
              state: slot2Verified ? 'CURRENT RUN MATCH' : 'CHECKING RUN…',
              col: C.emeraldPrimary,
              bg: '#062e24',
              icon: '✓',
            },
            {
              slot: '03',
              title: 'Policy Conjunction Evaluation',
              state: slot3Verified ? 'SATRA INCONCLUSIVE → REVIEW' : 'EVALUATING GATE…',
              col: C.amberPrimary,
              bg: C.amberBg,
              icon: '!',
            },
          ].map((row, idx) => (
            <g key={row.slot} transform={`translate(-230, ${-95 + idx * 72})`}>
              <rect x="0" y="0" width="460" height="58" rx="14" fill="#081424" stroke="#1e293b" strokeWidth="1.5" />
              <g transform="translate(24, 29)">
                <circle cx="0" cy="0" r="14" fill={row.bg} stroke={row.col} strokeWidth="1.5" />
                <text x="0" y="4.5" fill={row.col} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="800" textAnchor="middle">
                  {row.icon}
                </text>
              </g>
              <g transform="translate(54, 22)">
                <text x="0" y="0" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="700">
                  {row.title}
                </text>
                <text x="0" y="18" fill={row.col} fontFamily="'JetBrains Mono', monospace" fontSize="11" fontWeight="700">
                  {row.state}
                </text>
              </g>
            </g>
          ))}

          {/* Gate Bottom Result Pill */}
          <g transform="translate(0, 155)">
            <rect x="-180" y="-22" width="360" height="44" rx="22" fill={decisionBg} stroke={decisionColor} strokeWidth="2.5" />
            <text x="0" y="6" fill={decisionColor} fontFamily="system-ui, sans-serif" fontSize="18" fontWeight="900" letterSpacing="2" textAnchor="middle">
              BOUNDED GATE: {finalDecision}
            </text>
          </g>

          <text x="0" y="205" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="500" textAnchor="middle">
            Inconclusive evidence preserved · Automatic release blocked truthfully
          </text>
        </g>
      )}

      {/* 4. Gate Policy Conjunction Summary Card (f: 340 - 405) */}
      {summaryAppear > 0 && (
        <g transform="translate(560, 260)" opacity={summaryAppear}>
          <rect x="0" y="0" width="800" height="460" rx="24" fill="#0b1424" stroke="#334155" strokeWidth="2.5" />
          <g transform="translate(45, 50)">
            <text x="0" y="0" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="24" fontWeight="800">
              ASENT POLICY CONJUNCTION MATRIX
            </text>
            <text x="0" y="28" fill={C.textSecondary} fontFamily="system-ui, sans-serif" fontSize="14">
              All active security modules must prove bounds continuity for automated PASS
            </text>
          </g>

          {[
            {module: 'CAVR (Dependency)', condition: 'VERIFIED', policy: 'PASS', col: C.emeraldPrimary, bg: '#062e24'},
            {module: 'SATRA-RV (Application)', condition: 'INCONCLUSIVE (Docker 125)', policy: 'FLAGGED', col: C.amberPrimary, bg: C.amberBg},
            {module: 'SABLE (Infrastructure)', condition: 'PRESERVED', policy: 'PASS', col: C.emeraldPrimary, bg: '#062e24'},
          ].map((item, idx) => (
            <g key={item.module} transform={`translate(45, ${136 + idx * 72})`}>
              <line x1="0" y1="-8" x2="710" y2="-8" stroke="#1e293b" strokeWidth="1" />
              <text x="0" y="20" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="16" fontWeight="700">
                {item.module}
              </text>
              <text x="0" y="42" fill={item.col} fontFamily="'JetBrains Mono', monospace" fontSize="12" fontWeight="600">
                State: {item.condition}
              </text>
              <g transform="translate(560, 10)">
                <rect x="0" y="0" width="150" height="32" rx="16" fill={item.bg} stroke={item.col} strokeWidth="1.8" />
                <circle cx="20" cy="16" r="4" fill={item.col} />
                <text x="85" y="21" fill={item.col} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="800" textAnchor="middle">
                  {item.policy}
                </text>
              </g>
            </g>
          ))}

          <g transform="translate(45, 395)">
            <rect x="0" y="0" width="710" height="34" rx="8" fill="#1e1828" stroke="#78350f" strokeWidth="1" />
            <text x="355" y="22" fill={C.amberPrimary} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="700" letterSpacing="0.8" textAnchor="middle">
              FAIL-SAFE GATE POLICY · INCONCLUSIVE CANNOT SILENTLY PROMOTE TO SUCCESS
            </text>
          </g>
        </g>
      )}

      {/* 5. Final Supported ASENT Integrated Result Card (f: 405 - 450) */}
      {resultCardAppear > 0 && (
        <g transform="translate(360, 220)" opacity={resultCardAppear}>
          <rect x="0" y="0" width="1200" height="580" rx="32" fill="#0b1322" stroke={decisionColor} strokeWidth="3.5" filter="url(#glowEffect)" />
          <rect x="0" y="0" width="1200" height="580" rx="32" fill="#09111e" stroke={decisionColor} strokeWidth="2.5" />

          {/* Eyebrow */}
          <g transform="translate(600, 70)">
            <rect x="-210" y="-17" width="420" height="34" rx="17" fill="#291a07" stroke={C.amberPrimary} strokeWidth="1.8" />
            <text x="0" y="5" fill="#fef08a" fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="800" letterSpacing="1.5" textAnchor="middle">
              SUPPORTED ASENT INTEGRATED MECHANISM
            </text>
          </g>

          <text x="600" y="155" fill={C.textSecondary} fontFamily="system-ui, sans-serif" fontSize="26" fontWeight="600" textAnchor="middle">
            CONVERGED BOUNDED TRUST GATE DECISION
          </text>

          {/* Result Banner */}
          <g transform="translate(600, 245)">
            <rect x="-270" y="-48" width="540" height="96" rx="26" fill={decisionBg} stroke={decisionColor} strokeWidth="3.5" />
            <text x="0" y="18" fill={decisionColor} fontFamily="system-ui, sans-serif" fontSize="54" fontWeight="900" letterSpacing="2.5" textAnchor="middle">
              {finalDecision}
            </text>
          </g>

          {/* Evidence Details: 2 Stacked Rows for full width */}
          <g transform="translate(180, 360)">
            <line x1="0" y1="0" x2="840" y2="0" stroke="#1e293b" strokeWidth="1.5" />

            <g transform="translate(0, 32)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="600" letterSpacing="1">
                CONVERGED MULTI-MODULE EVIDENCE
              </text>
              <text x="0" y="24" fill={C.textPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="15" fontWeight="700">
                CAVR: Verified  ·  SATRA: Inconclusive  ·  SABLE: Preserved
              </text>
            </g>

            <g transform="translate(0, 95)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="600" letterSpacing="1">
                BOUNDED DECISION RATIONALE
              </text>
              <text x="0" y="24" fill={C.amberPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="15" fontWeight="700">
                Run {evidence.runId || 'c6f6239d62b4'}  ·  Inconclusive application change blocks automated release
              </text>
            </g>
          </g>

          <text x="600" y="535" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="14" fontWeight="500" textAnchor="middle">
            Fail-safe gate semantics · Stored evidence checked · Bounded to human review without false claims
          </text>
        </g>
      )}

      {/* Bottom Progress Bar */}
      <g transform="translate(90, 1020)">
        <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="500">
          LOCAL CONTROLLED VISUALIZATION · STORED EVIDENCE IS AUTHORITATIVE
        </text>
        <rect x="0" y="16" width="1740" height="4" rx="2" fill="#1e293b" />
        <rect x="0" y="16" width={(1740 * f) / INTEGRATED_FRAMES} height="4" rx="2" fill={C.cyanPrimary} />
      </g>
    </svg>
  );
};
