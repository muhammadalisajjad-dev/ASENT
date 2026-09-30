import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

export const SATRA_FRAMES = 600;

export type SATRAEvidence = {
  status: string;
  route: string;
  subject: string;
  expectedStatus: number;
  dockerExit: number | null;
  dockerBackend: string;
  ollamaAvailable: boolean;
  oracleDiagnosis: string;
  oracleReason: string;
  ruleId?: string;
  action?: string;
  counterfactual?: string;
  mutantOperator?: string;
  runId: string | null;
  stale: boolean;
  integrityValid: boolean;
};

export type Props = {
  evidence: SATRAEvidence;
};

// Design System Colors matching SABLE and CAVR masters
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

// IDE Editor Component for SATRA (Python application code & security diff)
const SATRAEditor: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  diffMode?: boolean;
}> = ({x, y, scale = 1, opacity = 1, diffMode = false}) => {
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
        app/security.py
      </text>
      <text x="680" y="32" fill="#64748b" fontFamily="monospace" fontSize="13">
        PYTHON 3.12
      </text>

      {diffMode ? (
        <g transform="translate(25, 75)">
          {/* Baseline Guard Highlight */}
          <rect x="38" y="10" width="730" height="32" rx="6" fill={C.redBg} stroke="rgba(239, 68, 68, 0.4)" strokeWidth="1" />
          <text x="15" y="32" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#f87171" fontWeight="700">-   </tspan>
            <tspan fill="#f87171" fontWeight="600">return user.id == invoice.owner_id or user.is_admin</tspan>
          </text>

          {/* Counterfactual Mutant Candidate */}
          <rect x="38" y="46" width="730" height="32" rx="6" fill={C.amberBg} stroke="rgba(251, 191, 36, 0.4)" strokeWidth="1" />
          <text x="15" y="68" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#fbbf24" fontWeight="700">+   </tspan>
            <tspan fill="#fbbf24" fontWeight="600">return True  # Counterfactual mutant bypass</tspan>
          </text>

          <text x="15" y="112" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">03  </tspan>
            <tspan fill="#c084fc" fontWeight="700">@app.get</tspan>
            <tspan fill="#38bdf8">("/invoices/&#123;invoice_id&#125;")</tspan>
          </text>
          <text x="15" y="146" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">04  </tspan>
            <tspan fill="#c084fc" fontWeight="700">def </tspan>
            <tspan fill="#fde047" fontWeight="600">get_invoice</tspan>
            <tspan fill="#f8fafc">(invoice_id, user=Depends(current_user)):</tspan>
          </text>
          <text x="15" y="180" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">05    </tspan>
            <tspan fill="#c084fc" fontWeight="700">if not </tspan>
            <tspan fill="#f8fafc">can_access_invoice(user, invoice):</tspan>
          </text>
          <text x="15" y="214" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">06      </tspan>
            <tspan fill="#f87171" fontWeight="700">raise </tspan>
            <tspan fill="#f87171">HTTPException(status_code=403)</tspan>
          </text>
        </g>
      ) : (
        <g transform="translate(25, 75)">
          <text x="15" y="34" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">01  </tspan>
            <tspan fill="#c084fc" fontWeight="700">def </tspan>
            <tspan fill="#fde047" fontWeight="600">can_access_invoice</tspan>
            <tspan fill="#f8fafc">(user, invoice):</tspan>
          </text>
          {/* Security Guard Highlight */}
          <rect x="38" y="44" width="730" height="34" rx="6" fill="rgba(52, 211, 153, 0.12)" stroke="rgba(52, 211, 153, 0.35)" strokeWidth="1.2" />
          <text x="15" y="68" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">02    </tspan>
            <tspan fill="#34d399" fontWeight="700">return </tspan>
            <tspan fill="#34d399" fontWeight="600">user.id == invoice.owner_id or user.is_admin</tspan>
          </text>
          <text x="15" y="112" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">03  </tspan>
            <tspan fill="#c084fc" fontWeight="700">@app.get</tspan>
            <tspan fill="#38bdf8">("/invoices/&#123;invoice_id&#125;")</tspan>
          </text>
          <text x="15" y="146" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">04  </tspan>
            <tspan fill="#c084fc" fontWeight="700">def </tspan>
            <tspan fill="#fde047" fontWeight="600">get_invoice</tspan>
            <tspan fill="#f8fafc">(invoice_id, user=Depends(current_user)):</tspan>
          </text>
          <text x="15" y="180" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">05    </tspan>
            <tspan fill="#c084fc" fontWeight="700">if not </tspan>
            <tspan fill="#f8fafc">can_access_invoice(user, invoice):</tspan>
          </text>
          <text x="15" y="214" fontFamily="'JetBrains Mono', monospace" fontSize="15">
            <tspan fill="#64748b">06      </tspan>
            <tspan fill="#f87171" fontWeight="700">raise </tspan>
            <tspan fill="#f87171">HTTPException(status_code=403)</tspan>
          </text>
        </g>
      )}
    </g>
  );
};

// Security Change Contract Hero Card
const ContractHero: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  route: string;
  subject: string;
  expectedStatus: number;
}> = ({x, y, scale = 1, opacity = 1, route, subject: _subject, expectedStatus}) => {
  return (
    <g transform={`translate(${x}, ${y}) scale(${scale})`} opacity={opacity}>
      <rect x="-180" y="-120" width="360" height="240" rx="24" fill="#0b1728" stroke={C.cyanPrimary} strokeWidth="2.5" />
      <g transform="translate(0, -96)">
        <rect x="-120" y="-14" width="240" height="28" rx="14" fill="#072033" stroke={C.cyanPrimary} strokeWidth="1.5" />
        <circle cx="-96" cy="0" r="4" fill={C.cyanPrimary} />
        <text x="8" y="4.5" fill="#a5f3fc" fontFamily="system-ui, sans-serif" fontSize="10.5" fontWeight="800" letterSpacing="0.8" textAnchor="middle">
          SECURITY CHANGE CONTRACT
        </text>
      </g>
      <text x="0" y="-45" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="18" fontWeight="800" textAnchor="middle">
        AUTHZ.IDOR.001
      </text>
      <text x="0" y="-24" fill={C.cyanPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="11" fontWeight="700" textAnchor="middle">
        SRS.md#FR-03 · Ownership Invariant
      </text>

      <line x1="-150" y1="-8" x2="150" y2="-8" stroke="#1e293b" strokeWidth="1" />

      <g transform="translate(-140, 16)">
        <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="600">
          PROTECTED ROUTE
        </text>
        <text x="0" y="20" fill={C.textPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="13" fontWeight="700">
          {route}
        </text>
      </g>

      <g transform="translate(-140, 68)">
        <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="600">
          EXPECTED CONTRACT OUTCOME
        </text>
        <text x="0" y="22" fill={C.emeraldPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="14" fontWeight="800">
          HTTP {expectedStatus} Forbidden
        </text>
      </g>

      <g transform="translate(0, 142)">
        <text x="0" y="0" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="22" fontWeight="800" textAnchor="middle">
          Change Contract
        </text>
        <text x="0" y="22" fill={C.cyanPrimary} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="700" letterSpacing="2" textAnchor="middle">
          FORMAL SPECIFICATION
        </text>
      </g>
    </g>
  );
};

// Disposable Sandbox Hero Component (reflects actual Docker exit 125 truth)
const SandboxHero: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  dockerExit: number | null;
  launchPulse?: number;
}> = ({x, y, scale = 1, opacity = 1, dockerExit, launchPulse = 0}) => {
  const isFailed = dockerExit !== 0 && dockerExit !== null;
  const borderCol = isFailed ? C.amberPrimary : C.emeraldPrimary;
  const glowCol = isFailed ? C.amberGlow : C.emeraldGlow;

  return (
    <g transform={`translate(${x}, ${y}) scale(${scale})`} opacity={opacity}>
      <ellipse cx="0" cy="115" rx="160" ry="32" fill={glowCol} opacity={0.7 + launchPulse * 0.3} />
      <ellipse cx="0" cy="115" rx="130" ry="20" fill="#030712" opacity={0.8} />

      {/* Outer Sandbox Vessel */}
      <rect x="-140" y="-85" width="280" height="190" rx="32" fill="url(#sandboxGrad)" stroke={borderCol} strokeWidth="3.5" />
      <rect x="-128" y="-73" width="256" height="166" rx="24" fill="none" stroke="rgba(251, 191, 36, 0.15)" strokeWidth="1" />

      {/* Header Chip */}
      <g transform="translate(0, -62)">
        <rect x="-105" y="-14" width="210" height="28" rx="14" fill="#261707" stroke={borderCol} strokeWidth="1.8" />
        <circle cx="-82" cy="0" r="4.5" fill={borderCol} />
        <text x="-64" y="4.5" fill="#fef3c7" fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="800" letterSpacing="0.8" textAnchor="start">
          DISPOSABLE SANDBOX
        </text>
      </g>

      {/* Docker Image / Execution Dial */}
      <g transform="translate(0, 15)">
        <circle cx="0" cy="0" r="34" fill="#1c1106" stroke={borderCol} strokeWidth="2.5" />
        <circle cx="0" cy="0" r="22" fill="none" stroke={borderCol} strokeWidth="1.5" strokeDasharray="4 4" />
        <text x="0" y="4" fill="#fbbf24" fontFamily="'JetBrains Mono', monospace" fontSize="11" fontWeight="800" textAnchor="middle">
          {dockerExit ? `EXIT ${dockerExit}` : 'SANDBOX'}
        </text>
      </g>

      {/* Image Status Pill */}
      <g transform="translate(0, 68)">
        <rect x="-95" y="-11" width="190" height="22" rx="11" fill="#38200d" stroke={C.amberPrimary} strokeWidth="1.2" />
        <text x="0" y="4" fill="#fef08a" fontFamily="'JetBrains Mono', monospace" fontSize="9.5" fontWeight="800" textAnchor="middle">
          asent-sandbox:local UNAVAILABLE
        </text>
      </g>

      {/* Bottom Labels */}
      <text x="0" y="170" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="24" fontWeight="800" textAnchor="middle">
        Docker Execution
      </text>
      <text x="0" y="196" fill={C.amberPrimary} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="700" letterSpacing="2" textAnchor="middle">
        CONTAINER EXIT 125 · NOT RUN
      </text>
    </g>
  );
};

export const SATRAFilm: React.FC<Props> = ({evidence}) => {
  const f = useCurrentFrame();

  const status = evidence.status || 'INCONCLUSIVE';
  const isSuccess = status === 'VERIFIED' || status === 'ACCEPT';
  const statusColor = isSuccess ? C.emeraldPrimary : C.amberPrimary;
  const statusBg = isSuccess ? '#062e24' : C.amberBg;

  // ----------------------------------------------------
  // Timing & Continuous Choreography (600 frames total, 30fps)
  // ----------------------------------------------------
  // 0 - 2.8s (f: 0 - 85)   : Developer IDE centered, security guard highlighted
  // 2.8 - 5.5s (f: 85 - 165): IDE moves top-left, Security Change Contract hero appears
  // 5.5 - 8.5s (f: 165 - 255): Disposable Sandbox enters; Docker launch attempted -> exit 125 revealed
  // 8.5 - 11.5s (f: 255 - 345): Conditional Ollama local service node (CONDITIONAL / NOT EXECUTED)
  // 11.5 - 14.5s (f: 345 - 435): Oracle Differential Diagnosis (Expected vs Actual, INCONCLUSIVE)
  // 14.5 - 17.0s (f: 435 - 510): Inconclusive Evidence Token recorded; Sandbox moves to x:540
  // 17.0 - 19.0s (f: 510 - 570): SATRA-RV Assurance Bounds card unfolds
  // 19.0 - 20.0s (f: 570 - 600): Final Supported SATRA-RV Result (INCONCLUSIVE)

  // Editor transition: Centers at start, glides to top-left
  const editorScale = move(f, 1.0, 0.55, 75, 110);
  const editorX = move(f, 550, 90, 75, 110);
  const editorY = move(f, 260, 150, 75, 110);
  const editorDiff = f >= 80;
  const editorOpacity = fade(f, 480, 510);

  // Security Change Contract Animation (f: 85 - 240)
  const contractAppear = appear(f, 85, 120);
  const contractX = f < 170 ? move(f, 450, 1080, 85, 120) : move(f, 1080, 680, 170, 200);
  const contractOpacity = f < 170 ? contractAppear : fade(f, 235, 255);

  // Contract Lineage Edge from IDE diff to Contract Hero (f: 110 - 170)
  const contractEdgeOpacity = interpolate(f, [110, 125, 160, 170], [0, 0.85, 0.85, 0], clamp);

  // Disposable Sandbox Hero Animation (Docker exit 125 truth)
  // Appears at x: 1200 at f: 170, shifts to x: 920 at f: 235-260, then glides to x: 540 at f: 475-505
  const sandboxAppear = appear(f, 170, 205);
  const sandboxX =
    f < 235
      ? 1200
      : f < 475
      ? move(f, 1200, 920, 235, 260)
      : move(f, 920, 540, 475, 505);
  const sandboxY = 500;
  const sandboxOpacity = f < 570 ? sandboxAppear : fade(f, 570, 580);

  // Launch Attempt Token from Contract into Sandbox (f: 195 - 225)
  const launchX = move(f, 820, 970, 195, 215);
  const launchOpacity = interpolate(f, [195, 202, 215, 222], [0, 1, 1, 0], clamp);
  const launchPulse = interpolate(f, [215, 222, 230, 240], [0, 1, 0.5, 0], clamp);

  // Conditional Ollama Local Service Node (f: 255 - 345)
  const ollamaAppear = interpolate(f, [255, 275, 335, 345], [0, 1, 1, 0], clamp);

  // Differential Oracle Card (f: 345 - 475)
  const oracleAppear = interpolate(f, [345, 365, 465, 480], [0, 1, 1, 0], clamp);

  // Evidence Token (f: 435 - 510)
  const tokenAppear = appear(f, 435, 460);

  // Bounds Panel (f: 510 - 570)
  const boundsAppear = interpolate(f, [510, 530, 565, 575], [0, 1, 1, 0], clamp);

  // Final Result Card (f: 572 - 600)
  const resultCardAppear = appear(f, 572, 585);

  return (
    <svg width="100%" height="100%" viewBox="0 0 1920 1080" style={{background: C.bg}}>
      <defs>
        <radialGradient id="stageGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#2e1065" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#080d16" stopOpacity="0" />
        </radialGradient>

        <linearGradient id="sandboxGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#2e1c0c" />
          <stop offset="50%" stopColor="#1c1106" />
          <stop offset="100%" stopColor="#080d16" />
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
          fill={C.amberPrimary}
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
          SATRA-RV · APPLICATION-CODE SECURITY CHANGE ASSURANCE
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
        <SATRAEditor x={editorX} y={editorY} scale={editorScale} opacity={editorOpacity} diffMode={editorDiff} />
      )}

      {/* Contract Invariant Connector Edge from IDE to Contract Hero (f: 110 - 170) */}
      {contractEdgeOpacity > 0 && (
        <g opacity={contractEdgeOpacity}>
          <path
            d="M 540 260 C 720 260, 840 450, 960 480"
            fill="none"
            stroke={C.cyanPrimary}
            strokeWidth="2.5"
            strokeDasharray="6 4"
          />
          <g transform="translate(740, 350)">
            <rect x="-85" y="-13" width="170" height="26" rx="13" fill="#072033" stroke={C.cyanPrimary} strokeWidth="1.2" />
            <text x="0" y="4.5" fill="#a5f3fc" fontFamily="system-ui, sans-serif" fontSize="10.5" fontWeight="800" textAnchor="middle">
              CONTRACT INVARIANT
            </text>
          </g>
        </g>
      )}

      {/* 2. Security Change Contract Hero (f: 85 - 250) */}
      {contractOpacity > 0 && (
        <ContractHero
          x={contractX}
          y={500}
          scale={1.0}
          opacity={contractOpacity}
          route={evidence.route || 'GET /invoices/{invoice_id}'}
          subject={evidence.subject || 'authenticated normal user'}
          expectedStatus={evidence.expectedStatus || 403}
        />
      )}

      {/* Launch Attempt: Command Token travels from Contract into Sandbox (f: 195 - 225) */}
      {launchOpacity > 0 && (
        <g
          transform={`translate(${launchX}, 500)`}
          opacity={launchOpacity}
        >
          <rect x="-90" y="-18" width="180" height="36" rx="18" fill="#1e1828" stroke={C.amberPrimary} strokeWidth="1.8" />
          <circle cx="-68" cy="0" r="4.5" fill={C.amberPrimary} />
          <text x="8" y="4.5" fill="#fef08a" fontFamily="'JetBrains Mono', monospace" fontSize="11" fontWeight="700" textAnchor="middle">
            docker run --rm
          </text>
        </g>
      )}

      {/* 3. Disposable Sandbox Hero (Docker exit 125 recorded truthfully) */}
      {sandboxOpacity > 0 && (
        <SandboxHero
          x={sandboxX}
          y={sandboxY}
          scale={1.0}
          opacity={sandboxOpacity}
          dockerExit={evidence.dockerExit !== undefined ? evidence.dockerExit : 125}
          launchPulse={launchPulse}
        />
      )}

      {/* Sandbox Launch Diagnostics Banner during Exit 125 (f: 215 - 250) */}
      {launchPulse > 0.1 && (
        <g
          transform="translate(1200, 330)"
          opacity={launchPulse}
        >
          <rect x="-170" y="-18" width="340" height="36" rx="18" fill="#38200d" stroke={C.amberPrimary} strokeWidth="1.8" />
          <circle cx="-145" cy="0" r="4.5" fill={C.amberPrimary} />
          <text x="10" y="4.5" fill="#fef08a" fontFamily="'JetBrains Mono', monospace" fontSize="11.5" fontWeight="800" textAnchor="middle">
            IMAGE UNAVAILABLE · EXIT CODE 125
          </text>
        </g>
      )}

      {/* 4. Conditional Local Ollama Infrastructure & Connector (Frames 255 - 345) */}
      {ollamaAppear > 0 && (
        <>
          {/* Inquiry Connector from Sandbox to Ollama */}
          <path
            d="M 920 380 Q 1170 290 1420 380"
            fill="none"
            stroke="#818cf8"
            strokeWidth="2.2"
            strokeDasharray="6 4"
            opacity={ollamaAppear * 0.8}
          />
          <g transform="translate(1170, 290)" opacity={ollamaAppear}>
            <rect x="-105" y="-13" width="210" height="26" rx="13" fill="#13101c" stroke="#818cf8" strokeWidth="1.2" />
            <text x="0" y="4.5" fill="#c7d2fe" fontFamily="system-ui, sans-serif" fontSize="10.5" fontWeight="800" textAnchor="middle">
              ADAPTIVE TEST SYNTHESIS
            </text>
          </g>

          {/* Ollama Service Node Card */}
          <g transform="translate(1420, 500)" opacity={ollamaAppear}>
            <rect x="-160" y="-110" width="320" height="220" rx="24" fill="#13101c" stroke="#6366f1" strokeWidth="2" strokeDasharray="6 4" />
            <g transform="translate(0, -86)">
              <rect x="-95" y="-13" width="190" height="26" rx="13" fill="#1f1838" stroke="#818cf8" strokeWidth="1.2" />
              <circle cx="-75" cy="0" r="4.5" fill="#818cf8" />
              <text x="8" y="4.5" fill="#c7d2fe" fontFamily="system-ui, sans-serif" fontSize="10.5" fontWeight="800" textAnchor="middle">
                CONDITIONAL LOCAL LLM
              </text>
            </g>

            <text x="0" y="-35" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="20" fontWeight="800" textAnchor="middle">
              Ollama Service
            </text>
            <text x="0" y="-12" fill="#a5b4fc" fontFamily="'JetBrains Mono', monospace" fontSize="11" fontWeight="600" textAnchor="middle">
              Infrastructure · Optional
            </text>

            <g transform="translate(0, 30)">
              <rect x="-120" y="-18" width="240" height="36" rx="18" fill="#2d1c07" stroke={C.amberPrimary} strokeWidth="1.8" />
              <circle cx="-95" cy="0" r="4.5" fill={C.amberPrimary} />
              <text x="10" y="4.5" fill="#fde047" fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="800" textAnchor="middle">
                NOT EXECUTED IN RUN
              </text>
            </g>

            <text x="0" y="80" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="500" textAnchor="middle">
              Optional Ollama disabled · No validations recorded
            </text>
          </g>
        </>
      )}

      {/* 5. Oracle Differential Diagnosis Node & Comparison Edge (Frames 345 - 480) */}
      {oracleAppear > 0 && (
        <>
          {/* Differential Comparison Arc */}
          <path
            d="M 920 380 Q 1170 290 1420 380"
            fill="none"
            stroke={C.amberPrimary}
            strokeWidth="2.2"
            strokeDasharray="6 4"
            opacity={oracleAppear * 0.8}
          />
          <g transform="translate(1170, 290)" opacity={oracleAppear}>
            <rect x="-110" y="-13" width="220" height="26" rx="13" fill="#291a07" stroke={C.amberPrimary} strokeWidth="1.2" />
            <text x="0" y="4.5" fill="#fde047" fontFamily="system-ui, sans-serif" fontSize="10.5" fontWeight="800" textAnchor="middle">
              DIFFERENTIAL COMPARISON
            </text>
          </g>

          {/* Differential Oracle Card */}
          <g transform="translate(1420, 500)" opacity={oracleAppear}>
            <rect x="-210" y="-135" width="420" height="270" rx="24" fill="#0f172a" stroke={C.amberPrimary} strokeWidth="2.5" />
            <g transform="translate(0, -110)">
              <rect x="-120" y="-14" width="240" height="28" rx="14" fill="#291a07" stroke={C.amberPrimary} strokeWidth="1.5" />
              <circle cx="-98" cy="0" r="4.5" fill={C.amberPrimary} />
              <text x="8" y="4.5" fill="#fde047" fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="800" textAnchor="middle">
                DIFFERENTIAL ORACLE
              </text>
            </g>

            <g transform="translate(-175, -55)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="600">
                EXPECTED CONTRACT
              </text>
              <text x="0" y="20" fill={C.emeraldPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="13" fontWeight="800">
                HTTP {evidence.expectedStatus || 403} (Guard Enforced)
              </text>
            </g>

            <g transform="translate(-175, 5)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="600">
                ACTUAL RUNTIME OBSERVATION
              </text>
              <text x="0" y="20" fill={C.amberPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="13" fontWeight="800">
                Skipped · Docker Exit {evidence.dockerExit ?? 125}
              </text>
            </g>

            <g transform="translate(0, 68)">
              <rect x="-175" y="-18" width="350" height="36" rx="18" fill="#38200d" stroke={C.amberPrimary} strokeWidth="1.8" />
              <text x="0" y="5" fill="#fbbf24" fontFamily="'JetBrains Mono', monospace" fontSize="12" fontWeight="800" textAnchor="middle">
                DIAGNOSIS: INCONCLUSIVE
              </text>
            </g>

            <text x="0" y="112" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="11" fontWeight="500" textAnchor="middle">
              Counterfactual not independently shown to violate contract
            </text>
          </g>
        </>
      )}

      {/* 6. Evidence Token Captured (Frames 435 - 510) */}
      {tokenAppear > 0 && f < 510 && (
        <g transform="translate(1170, 220)" opacity={tokenAppear}>
          <rect x="-240" y="-22" width="480" height="44" rx="22" fill="#1e1828" stroke={C.amberPrimary} strokeWidth="2.2" />
          <circle cx="-205" cy="0" r="12" fill={C.amberPrimary} />
          <text x="-205" y="4.5" fill="#38200d" fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="900" textAnchor="middle">
            !
          </text>
          <text x="15" y="5.5" fill="#fef08a" fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="800" letterSpacing="1.2" textAnchor="middle">
            SATRA EVIDENCE: INCONCLUSIVE RECORDED
          </text>
        </g>
      )}

      {/* 7. SATRA-RV Assurance Bounds Card (Frames 510 - 570) */}
      {boundsAppear > 0 && (
        <g transform="translate(860, 290)" opacity={boundsAppear}>
          <rect x="0" y="0" width="840" height="420" rx="24" fill="#0b1424" stroke="#334155" strokeWidth="2.5" />
          <g transform="translate(45, 52)">
            <text x="0" y="0" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="24" fontWeight="800">
              SATRA-RV APPLICATION ASSURANCE BOUNDS
            </text>
            <text x="0" y="28" fill={C.textSecondary} fontFamily="system-ui, sans-serif" fontSize="14">
              Auditable security contract evaluation limits for application code change
            </text>
          </g>

          {[
            {label: `Security Change Contract (${evidence.ruleId || 'AUTHZ.IDOR.001'})`, status: 'ESTABLISHED', col: C.emeraldPrimary, bg: '#062e24'},
            {label: 'Sandbox Environment (Docker)', status: `EXIT ${evidence.dockerExit ?? 125}`, col: C.amberPrimary, bg: C.amberBg},
            {label: 'Adaptive Local Model (Ollama)', status: 'NOT EXECUTED', col: C.amberPrimary, bg: C.amberBg},
            {label: 'Differential Oracle Diagnosis', status: 'INCONCLUSIVE', col: C.amberPrimary, bg: C.amberBg},
          ].map((item, idx) => (
            <g key={item.label} transform={`translate(45, ${134 + idx * 56})`}>
              <line x1="0" y1="-6" x2="750" y2="-6" stroke="#1e293b" strokeWidth="1" />
              <text x="0" y="22" fill={C.textPrimary} fontFamily="system-ui, sans-serif" fontSize="16" fontWeight="600">
                {item.label}
              </text>
              <g transform="translate(580, 0)">
                <rect x="0" y="0" width="160" height="32" rx="16" fill={item.bg} stroke={item.col} strokeWidth="1.8" />
                <circle cx="20" cy="16" r="4" fill={item.col} />
                <text x="88" y="21" fill={item.col} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="800" textAnchor="middle">
                  {item.status}
                </text>
              </g>
            </g>
          ))}

          <g transform="translate(45, 362)">
            <rect x="0" y="0" width="750" height="34" rx="8" fill="#1e1828" stroke="#78350f" strokeWidth="1" />
            <text x="375" y="22" fill={C.amberPrimary} fontFamily="system-ui, sans-serif" fontSize="12" fontWeight="700" letterSpacing="0.8" textAnchor="middle">
              BOUNDED ASSURANCE · INCONCLUSIVE PRESERVED WITHOUT FALSE SUCCESS
            </text>
          </g>
        </g>
      )}

      {/* 8. Final Supported SATRA-RV Result (Frames 572 - 600) */}
      {resultCardAppear > 0 && (
        <g transform="translate(360, 220)" opacity={resultCardAppear}>
          <rect x="0" y="0" width="1200" height="580" rx="32" fill="#0b1322" stroke={statusColor} strokeWidth="3.5" filter="url(#glowEffect)" />
          <rect x="0" y="0" width="1200" height="580" rx="32" fill="#09111e" stroke={statusColor} strokeWidth="2.5" />

          {/* Eyebrow */}
          <g transform="translate(600, 70)">
            <rect x="-190" y="-17" width="380" height="34" rx="17" fill="#291a07" stroke={C.amberPrimary} strokeWidth="1.8" />
            <text x="0" y="5" fill="#fef08a" fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="800" letterSpacing="1.5" textAnchor="middle">
              SUPPORTED SATRA-RV MECHANISM
            </text>
          </g>

          <text x="600" y="155" fill={C.textSecondary} fontFamily="system-ui, sans-serif" fontSize="26" fontWeight="600" textAnchor="middle">
            APPLICATION SECURITY CHANGE ASSURANCE
          </text>

          {/* Result Banner */}
          <g transform="translate(600, 245)">
            <rect x="-270" y="-48" width="540" height="96" rx="26" fill={statusBg} stroke={statusColor} strokeWidth="3.5" />
            <text x="0" y="18" fill={statusColor} fontFamily="system-ui, sans-serif" fontSize="54" fontWeight="900" letterSpacing="2.5" textAnchor="middle">
              {status}
            </text>
          </g>

          {/* Evidence Details */}
          <g transform="translate(180, 370)">
            <line x1="0" y1="0" x2="840" y2="0" stroke="#1e293b" strokeWidth="1.5" />

            <g transform="translate(0, 42)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="600">
                SECURITY CHANGE CONTRACT
              </text>
              <text x="0" y="28" fill={C.textPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="16" fontWeight="700">
                {evidence.ruleId || 'AUTHZ.IDOR.001'} · {evidence.route || 'GET /invoices/{invoice_id}'}
              </text>
            </g>

            <g transform="translate(480, 42)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="600">
                EVIDENCE RUN IDENTIFIER
              </text>
              <text x="0" y="28" fill={C.textPrimary} fontFamily="'JetBrains Mono', monospace" fontSize="16" fontWeight="700">
                {evidence.runId || 'c6f6239d62b4'} · Docker Exit {evidence.dockerExit ?? 125}
              </text>
            </g>
          </g>

          <text x="600" y="525" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="14" fontWeight="500" textAnchor="middle">
            Truthful bounded outcome · Docker exit 125 recorded · INCONCLUSIVE preserved without false success
          </text>
        </g>
      )}

      {/* Bottom Progress Bar */}
      <g transform="translate(90, 1020)">
        <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, sans-serif" fontSize="13" fontWeight="500">
          LOCAL CONTROLLED VISUALIZATION · STORED EVIDENCE IS AUTHORITATIVE
        </text>
        <rect x="0" y="16" width="1740" height="4" rx="2" fill="#1e293b" />
        <rect x="0" y="16" width={(1740 * f) / SATRA_FRAMES} height="4" rx="2" fill={C.amberPrimary} />
      </g>
    </svg>
  );
};
