import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

export const SABLE_FRAMES = 600;

export type Evidence = {
  status: string;
  successor: string | null;
  runId: string | null;
  finalDecision: string;
  reasons: string[];
  stale: boolean;
  integrityValid: boolean;
};

export type Props = {
  evidence: Evidence;
};

// Design System Colors
const C = {
  bg: '#080d16',
  cardBg: '#0f172a',
  cardBorder: '#1e293b',
  textMuted: '#64748b',
  textSecondary: '#94a3b8',
  textPrimary: '#f8fafc',
  violetPrimary: '#818cf8',
  violetDark: '#312e81',
  violetGlow: 'rgba(99, 102, 241, 0.28)',
  cyanPrimary: '#22d3ee',
  cyanGlow: 'rgba(34, 211, 238, 0.25)',
  emeraldPrimary: '#34d399',
  emeraldDark: '#065f46',
  emeraldGlow: 'rgba(52, 211, 153, 0.3)',
  amberPrimary: '#fbbf24',
  amberDark: '#78350f',
  amberBg: '#38200d',
  redPrimary: '#f87171',
  redBg: 'rgba(239, 68, 68, 0.15)',
};

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

const appear = (f: number, start: number, end: number) => interpolate(f, [start, end], [0, 1], clamp);
const fade = (f: number, start: number, end: number) => interpolate(f, [start, end], [1, 0], clamp);
const move = (f: number, a: number, b: number, start: number, end: number) =>
  interpolate(f, [start, end], [a, b], {...clamp, easing: easeInOut});

// Vector S3 Cloud Storage Hero Component
const S3BucketHero: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  label?: string;
  sublabel?: string;
  isNew?: boolean;
  highlightGlow?: number;
}> = ({
  x,
  y,
  scale = 1,
  opacity = 1,
  label = 'invoice_data',
  sublabel = 'S3 BUCKET · CLOUD STORAGE',
  isNew = false,
  highlightGlow = 0,
}) => {
  const accent = isNew ? C.emeraldPrimary : C.violetPrimary;
  const glowCol = isNew ? C.emeraldGlow : C.violetGlow;

  return (
    <g transform={`translate(${x}, ${y}) scale(${scale})`} opacity={opacity}>
      {/* Base drop-shadow & pedestal glow */}
      <ellipse cx="0" cy="135" rx="155" ry="34" fill={glowCol} opacity={0.65 + highlightGlow * 0.35} />
      <ellipse cx="0" cy="135" rx="125" ry="22" fill="#030712" opacity={0.75} />

      {/* Main Cylinder Body */}
      <path
        d="M -125 0 L -125 105 C -125 140 125 140 125 105 L 125 0 Z"
        fill="url(#s3BodyGrad)"
        stroke={accent}
        strokeWidth="3.5"
      />

      {/* Storage Tier Platters (Layered Disks) */}
      <g opacity={0.92}>
        {/* Tier 1 divider */}
        <path d="M -123 34 C -123 62 123 62 123 34" fill="none" stroke="#4338ca" strokeWidth="2.5" />
        {/* Tier 2 divider */}
        <path d="M -123 70 C -123 98 123 98 123 70" fill="none" stroke="#4338ca" strokeWidth="2.5" />

        {/* Storage disk LED status indicators */}
        <circle cx="-85" cy="46" r="3.5" fill={accent} />
        <circle cx="-70" cy="48" r="3.5" fill={accent} opacity={0.6} />
        <circle cx="-55" cy="49" r="3.5" fill={accent} opacity={0.3} />

        <circle cx="-85" cy="82" r="3.5" fill={accent} />
        <circle cx="-70" cy="84" r="3.5" fill={accent} opacity={0.6} />
        <circle cx="-55" cy="85" r="3.5" fill={accent} opacity={0.3} />
      </g>

      {/* Top Aperture / Rim */}
      <ellipse cx="0" cy="0" rx="125" ry="35" fill="#1e1b4b" stroke={accent} strokeWidth="3.5" />
      <ellipse cx="0" cy="0" rx="100" ry="25" fill="url(#s3TopGrad)" stroke="#6366f1" strokeWidth="1.5" />

      {/* AWS S3 Badge Emblem */}
      <g transform="translate(0, 16)">
        <rect x="-46" y="-14" width="92" height="28" rx="14" fill="#0b1320" stroke={accent} strokeWidth="2" />
        <text
          x="0"
          y="5"
          fill="#f8fafc"
          fontFamily="system-ui, -apple-system, sans-serif"
          fontSize="14"
          fontWeight="800"
          letterSpacing="1.5"
          textAnchor="middle"
        >
          S3
        </text>
      </g>

      {/* Floating Data Object Particles (Cloud Storage Indicator) */}
      <g transform="translate(68, -46)">
        <rect
          x="-14"
          y="-14"
          width="28"
          height="28"
          rx="6"
          fill="#1e293b"
          stroke={C.cyanPrimary}
          strokeWidth="1.8"
          transform="rotate(12)"
        />
        <text x="0" y="4" fill={C.cyanPrimary} fontSize="11" fontWeight="700" textAnchor="middle">
          obj
        </text>
      </g>
      <g transform="translate(-70, -40)">
        <rect
          x="-12"
          y="-12"
          width="24"
          height="24"
          rx="5"
          fill="#1e293b"
          stroke={C.violetPrimary}
          strokeWidth="1.6"
          transform="rotate(-8)"
        />
        <text x="0" y="3.5" fill={C.violetPrimary} fontSize="10" fontWeight="700" textAnchor="middle">
          dat
        </text>
      </g>

      {/* Hero Labels */}
      <text
        x="0"
        y="178"
        fill={C.textPrimary}
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="28"
        fontWeight="700"
        textAnchor="middle"
        letterSpacing="0.5"
      >
        {label}
      </text>
      <text
        x="0"
        y="204"
        fill={accent}
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="13"
        fontWeight="650"
        letterSpacing="2.5"
        textAnchor="middle"
        opacity={0.9}
      >
        {sublabel}
      </text>
    </g>
  );
};

// IAM Role Principal Component
const IAMRolePrincipal: React.FC<{
  x: number;
  y: number;
  opacity?: number;
}> = ({x, y, opacity = 1}) => {
  return (
    <g transform={`translate(${x}, ${y})`} opacity={opacity}>
      {/* Glow */}
      <circle cx="0" cy="0" r="58" fill={C.cyanGlow} />

      {/* Outer identity card */}
      <rect
        x="-70"
        y="-70"
        width="140"
        height="140"
        rx="36"
        fill="#091824"
        stroke={C.cyanPrimary}
        strokeWidth="3"
      />

      {/* IAM Shield & Key Icon */}
      <g transform="translate(0, -6)">
        <path
          d="M 0 -34 L 28 -20 L 28 8 C 28 26 0 38 0 38 C 0 38 -28 26 -28 8 L -28 -20 Z"
          fill="#0c2a38"
          stroke={C.cyanPrimary}
          strokeWidth="2.5"
        />
        <circle cx="0" cy="-6" r="9" fill="none" stroke={C.cyanPrimary} strokeWidth="2.5" />
        <path d="M -12 16 C -12 7 12 7 12 16" fill="none" stroke={C.cyanPrimary} strokeWidth="2.5" />
      </g>

      {/* Role Labels */}
      <text
        x="0"
        y="105"
        fill={C.textPrimary}
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="22"
        fontWeight="700"
        textAnchor="middle"
      >
        application-role
      </text>
      <text
        x="0"
        y="128"
        fill={C.cyanPrimary}
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="12"
        fontWeight="650"
        letterSpacing="2"
        textAnchor="middle"
        opacity={0.9}
      >
        IAM PRINCIPAL
      </text>
    </g>
  );
};

// Professional IDE Editor Component with perfect SVG tspan typography
const TerraformEditor: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  diffMode?: boolean;
}> = ({x, y, scale = 1, opacity = 1, diffMode = false}) => {
  return (
    <g transform={`translate(${x}, ${y}) scale(${scale})`} opacity={opacity}>
      {/* Editor Window Shell */}
      <rect
        x="0"
        y="0"
        width="820"
        height="440"
        rx="16"
        fill="#0b1320"
        stroke="#1e293b"
        strokeWidth="2.5"
      />

      {/* Window Title Bar */}
      <path d="M 0 52 L 820 52" stroke="#1e293b" strokeWidth="2" />
      {/* Traffic lights */}
      <circle cx="26" cy="26" r="6.5" fill="#ef4444" />
      <circle cx="48" cy="26" r="6.5" fill="#f59e0b" />
      <circle cx="70" cy="26" r="6.5" fill="#10b981" />

      {/* Tab */}
      <rect x="105" y="10" width="180" height="34" rx="8" fill="#131e33" stroke="#263852" strokeWidth="1" />
      <path d="M 124 22 L 129 27 L 124 32 L 119 27 Z" fill="#a855f7" />
      <text
        x="138"
        y="32"
        fill="#cbd5e1"
        fontFamily="monospace"
        fontSize="14"
        fontWeight="600"
      >
        storage.tf
      </text>

      {/* Editor Mode Badge */}
      {diffMode ? (
        <g transform="translate(610, 15)">
          <rect x="0" y="0" width="180" height="25" rx="6" fill="#1e1828" stroke="#f43f5e" strokeWidth="1" />
          <text x="90" y="17" fill="#fb7185" fontFamily="sans-serif" fontSize="11" fontWeight="700" textAnchor="middle" letterSpacing="1">
            TERRAFORM REFACTOR
          </text>
        </g>
      ) : (
        <text x="730" y="32" fill="#64748b" fontFamily="monospace" fontSize="13">
          HCL 2.0
        </text>
      )}

      {/* Syntax-Highlighted Code Lines using <tspan> for robust text advancement */}
      {diffMode ? (
        <g transform="translate(25, 75)">
          {/* Deletion Line */}
          <rect x="38" y="14" width="730" height="32" rx="6" fill={C.redBg} stroke="rgba(239, 68, 68, 0.4)" strokeWidth="1" />
          <text x="15" y="36" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#f87171" fontWeight="700">-   </tspan>
            <tspan fill="#f87171" fontWeight="600">resource "aws_s3_bucket" "invoice_data" &#123;</tspan>
          </text>

          {/* Addition Line */}
          <rect x="38" y="50" width="730" height="32" rx="6" fill="rgba(16, 185, 129, 0.15)" stroke="rgba(16, 185, 129, 0.4)" strokeWidth="1" />
          <text x="15" y="72" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#34d399" fontWeight="700">+   </tspan>
            <tspan fill="#34d399" fontWeight="600">module.storage.aws_s3_bucket.data</tspan>
          </text>

          {/* Context Lines */}
          <text x="15" y="112" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">03  </tspan>
            <tspan fill="#cbd5e1">&#125;</tspan>
          </text>
          <text x="15" y="148" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">04  </tspan>
            <tspan fill="#818cf8" fontWeight="600">resource </tspan>
            <tspan fill="#38bdf8">"aws_iam_role_policy" </tspan>
            <tspan fill="#fde047" fontWeight="600">"app_access" </tspan>
            <tspan fill="#f8fafc">&#123;</tspan>
          </text>
          <text x="15" y="184" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">05    </tspan>
            <tspan fill="#94a3b8">action = </tspan>
            <tspan fill="#38bdf8">["s3:GetObject"]</tspan>
          </text>
          <text x="15" y="220" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">06    </tspan>
            <tspan fill="#94a3b8">resource = </tspan>
            <tspan fill="#34d399" fontWeight="600">module.storage.aws_s3_bucket.data.arn</tspan>
          </text>
          <text x="15" y="256" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">07  </tspan>
            <tspan fill="#cbd5e1">&#125;</tspan>
          </text>
        </g>
      ) : (
        <g transform="translate(25, 75)">
          {/* Resource 1: S3 Bucket */}
          <rect x="38" y="14" width="730" height="96" rx="8" fill="rgba(99, 102, 241, 0.08)" stroke="rgba(99, 102, 241, 0.3)" strokeWidth="1.2" />
          <text x="15" y="38" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">01  </tspan>
            <tspan fill="#c084fc" fontWeight="700">resource </tspan>
            <tspan fill="#38bdf8">"aws_s3_bucket" </tspan>
            <tspan fill="#fde047" fontWeight="600">"invoice_data" </tspan>
            <tspan fill="#f8fafc">&#123;</tspan>
          </text>
          <text x="15" y="72" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">02    </tspan>
            <tspan fill="#94a3b8">bucket = </tspan>
            <tspan fill="#34d399">"invoice-data-prod"</tspan>
          </text>
          <text x="15" y="102" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">03  </tspan>
            <tspan fill="#f8fafc">&#125;</tspan>
          </text>

          {/* Resource 2: IAM Role Policy */}
          <text x="15" y="152" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">04  </tspan>
            <tspan fill="#c084fc" fontWeight="700">resource </tspan>
            <tspan fill="#38bdf8">"aws_iam_role_policy" </tspan>
            <tspan fill="#fde047" fontWeight="600">"app_access" </tspan>
            <tspan fill="#f8fafc">&#123;</tspan>
          </text>
          <text x="15" y="186" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">05    </tspan>
            <tspan fill="#94a3b8">role   = </tspan>
            <tspan fill="#f8fafc">aws_iam_role.application_role.id</tspan>
          </text>
          <text x="15" y="220" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">06    </tspan>
            <tspan fill="#94a3b8">action = </tspan>
            <tspan fill="#38bdf8">["s3:GetObject"]</tspan>
          </text>
          <text x="15" y="254" fontFamily="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" fontSize="15">
            <tspan fill="#64748b">07  </tspan>
            <tspan fill="#f8fafc">&#125;</tspan>
          </text>
        </g>
      )}
    </g>
  );
};

// Main SABLE Visualization Film
export const SableFilm: React.FC<Props> = ({evidence}) => {
  const f = useCurrentFrame();

  const status = evidence.status || 'PRESERVED';
  const isPreserved = status === 'PRESERVED';
  const statusColor = isPreserved ? C.emeraldPrimary : status === 'REGRESSED' ? C.redPrimary : C.amberPrimary;
  const successorName = 'module.storage.aws_s3_bucket.data';

  // ----------------------------------------------------
  // Timing & Continuous Choreography (600 frames total)
  // ----------------------------------------------------
  // 0 - 2.8s (f: 0 - 85)   : Terraform IDE centered
  // 2.8 - 5.5s (f: 85 - 165): IDE slides up-left, S3 bucket materializes as hero
  // 5.5 - 8.0s (f: 165 - 240): IAM Role enters, draws authorization connection
  // 8.0 - 12.0s (f: 240 - 360): Terraform refactor diff, bucket moves old -> new
  // 12.0 - 15.0s (f: 360 - 450): Successor lineage trail follows bucket
  // 15.0 - 17.0s (f: 450 - 510): Authorization continuity check (✓)
  // 17.0 - 19.0s (f: 510 - 570): S3 Obligations shown (UNKNOWN, unevaluated)
  // 19.0 - 20.0s (f: 570 - 600): Final Supported SABLE Result (PRESERVED)

  // Editor transition: Centers at start, glides to top-left, fades during final result
  const editorScale = move(f, 1.0, 0.55, 75, 110);
  const editorX = move(f, 550, 90, 75, 110);
  const editorY = move(f, 260, 150, 75, 110);
  const editorDiff = f >= 235;
  const editorOpacity = fade(f, 500, 520);

  // Materialization beam (Code -> S3 Bucket)
  const beamOpacity = interpolate(f, [80, 100, 125, 145], [0, 1, 1, 0], clamp);

  // Bucket Hero Motion & Lifecycle
  const bucketMaterialize = appear(f, 85, 120);
  // Bucket coordinates:
  // Starts at 1080 (3-8s)
  // Moves to 1480 (8-12s, f: 255 to 335)
  // Stays at 1480 (12-17s)
  // Moves to 540 (17-19s, f: 505 to 535) to give full stage to obligations card
  const bucketX =
    f < 255
      ? 1080
      : f < 505
      ? move(f, 1080, 1480, 255, 335)
      : move(f, 1480, 540, 505, 535);

  const bucketY = 500;
  const isMigrated = f >= 335;
  const bucketScale = interpolate(f, [85, 120], [0.35, 1.0], {...clamp, easing: easeInOut});
  const bucketOpacity = f < 570 ? bucketMaterialize : fade(f, 570, 580);

  // IAM Principal Role Lifecycle
  // Slides in at f: 165-190, fades at f: 500-520
  const roleEnter = appear(f, 165, 190);
  const roleFade = fade(f, 500, 520);
  const roleOpacity = roleEnter * roleFade;
  const roleX = move(f, 160, 320, 165, 190);
  const roleY = 500;

  // Authorization Beam Lifecycle
  // Initial line drawing: f: 180 to 205
  const lineProgress1 = interpolate(f, [180, 205], [0, 1], clamp);
  // Re-connect to successor after refactor: f: 345 to 375
  const lineProgress2 = interpolate(f, [345, 375], [0, 1], clamp);

  // Continuity check badge at successor
  const checkBadgeAppear = appear(f, 385, 410);

  // Lineage trail: Elevated high arc well above containers
  const lineageTrailOpacity = interpolate(f, [255, 275, 480, 495], [0, 1, 1, 0], clamp);

  // Obligations Panel (17 - 19s)
  const obligationsAppear = interpolate(f, [515, 535, 565, 575], [0, 1, 1, 0], clamp);

  // Final Result Card (19 - 20s)
  const resultCardAppear = appear(f, 572, 585);

  return (
    <svg width="100%" height="100%" viewBox="0 0 1920 1080" style={{background: C.bg}}>
      <defs>
        {/* Gradients */}
        <radialGradient id="stageGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#1e1b4b" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#080d16" stopOpacity="0" />
        </radialGradient>

        <linearGradient id="s3BodyGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#2e256b" />
          <stop offset="50%" stopColor="#1e1b4b" />
          <stop offset="100%" stopColor="#0f172a" />
        </linearGradient>

        <radialGradient id="s3TopGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#4f46e5" />
          <stop offset="70%" stopColor="#312e81" />
          <stop offset="100%" stopColor="#1e1b4b" />
        </radialGradient>

        <linearGradient id="cyanLineGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#38bdf8" />
        </linearGradient>

        <filter id="glowEffect" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="8" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Stage Background */}
      <rect width="1920" height="1080" fill={C.bg} />
      <circle cx="960" cy="540" r="750" fill="url(#stageGlow)" />

      {/* Modern Technical Grid Background */}
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
          fill={C.violetPrimary}
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
          SABLE · RESOURCE &amp; AUTHORIZATION CONTINUITY
        </text>
      </g>

      {/* Subtle Controlled Model Label in Top Right */}
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

      {/* ==================================================== */}
      {/* 1. TERRAFORM CODE EDITOR (Continuous In-Place Node) */}
      {/* ==================================================== */}
      {editorOpacity > 0 && (
        <TerraformEditor
          x={editorX}
          y={editorY}
          scale={editorScale}
          opacity={editorOpacity}
          diffMode={editorDiff}
        />
      )}

      {/* Materialization Beam (Code -> S3 Bucket) */}
      {beamOpacity > 0 && (
        <path
          d={`M ${editorX + 460 * editorScale} ${editorY + 110 * editorScale} Q 800 250 1080 430`}
          fill="none"
          stroke={C.violetPrimary}
          strokeWidth="3.5"
          strokeDasharray="8 6"
          strokeLinecap="round"
          opacity={beamOpacity}
        />
      )}

      {/* ==================================================== */}
      {/* 2. INFRASTRUCTURE WORLD (Old & Successor Context)   */}
      {/* ==================================================== */}
      {/* Old Resource Container Boundary (Ghost Outline - fades once bucket migrates) */}
      {f >= 240 && f < 370 && (
        <g
          transform="translate(1080, 500)"
          opacity={interpolate(f, [240, 260, 340, 365], [0, 0.65, 0.65, 0], clamp)}
        >
          <rect
            x="-160"
            y="-150"
            width="320"
            height="300"
            rx="20"
            fill="none"
            stroke="#475569"
            strokeWidth="2"
            strokeDasharray="8 8"
          />
          <rect
            x="-140"
            y="-166"
            width="280"
            height="30"
            rx="15"
            fill="#0b1320"
            stroke="#475569"
            strokeWidth="1.5"
          />
          <text
            x="0"
            y="-146"
            fill="#94a3b8"
            fontFamily="monospace"
            fontSize="12"
            fontWeight="600"
            textAnchor="middle"
          >
            OLD: aws_s3_bucket.invoice_data
          </text>
        </g>
      )}

      {/* Successor Module Container Boundary */}
      {f >= 250 && f < 500 && (
        <g
          transform="translate(1480, 500)"
          opacity={interpolate(f, [250, 275, 480, 500], [0, 1, 1, 0], clamp)}
        >
          <rect
            x="-170"
            y="-150"
            width="340"
            height="300"
            rx="22"
            fill="rgba(15, 23, 42, 0.75)"
            stroke={isMigrated ? C.emeraldPrimary : '#334155'}
            strokeWidth="2.5"
          />
          <rect
            x="-130"
            y="-166"
            width="260"
            height="32"
            rx="16"
            fill="#091824"
            stroke={isMigrated ? C.emeraldPrimary : '#334155'}
            strokeWidth="1.5"
          />
          <text
            x="0"
            y="-145"
            fill={isMigrated ? C.emeraldPrimary : C.textSecondary}
            fontFamily="monospace"
            fontSize="13"
            fontWeight="700"
            textAnchor="middle"
          >
            module.storage
          </text>
        </g>
      )}

      {/* Successor Lineage Trail (High Arc cleanly above containers) */}
      {lineageTrailOpacity > 0 && (
        <g opacity={lineageTrailOpacity}>
          <path
            d="M 1080 340 Q 1280 190 1480 340"
            fill="none"
            stroke={C.violetPrimary}
            strokeWidth="3.5"
            strokeDasharray="10 8"
            strokeDashoffset={-f * 4}
          />
          <g transform="translate(1280, 190)">
            <rect
              x="-95"
              y="-17"
              width="190"
              height="34"
              rx="17"
              fill="#131e33"
              stroke={C.violetPrimary}
              strokeWidth="2"
            />
            <text
              x="0"
              y="5"
              fill="#c7d2fe"
              fontFamily="system-ui, -apple-system, sans-serif"
              fontSize="12"
              fontWeight="700"
              letterSpacing="1"
              textAnchor="middle"
            >
              SUCCESSOR LINEAGE
            </text>
          </g>
        </g>
      )}

      {/* ==================================================== */}
      {/* 3. IAM PRINCIPAL ROLE (Application Role)             */}
      {/* ==================================================== */}
      {roleOpacity > 0 && (
        <IAMRolePrincipal x={roleX} y={roleY} opacity={roleOpacity} />
      )}

      {/* ==================================================== */}
      {/* 4. AUTHORIZATION RELATIONSHIP & CONTINUITY BEAM     */}
      {/* ==================================================== */}
      {/* Initial Connection (Frames 180 - 255) */}
      {roleOpacity > 0 && f < 255 && (
        <g>
          <line
            x1="390"
            y1={roleY}
            x2="950"
            y2={roleY}
            stroke="#1e293b"
            strokeWidth="4"
          />
          <line
            x1="390"
            y1={roleY}
            x2={390 + (950 - 390) * lineProgress1}
            y2={roleY}
            stroke="url(#cyanLineGrad)"
            strokeWidth="4"
            strokeLinecap="round"
          />
          {lineProgress1 > 0.3 && (
            <g transform="translate(670, 500)">
              <rect
                x="-85"
                y="-20"
                width="170"
                height="40"
                rx="20"
                fill="#082333"
                stroke={C.cyanPrimary}
                strokeWidth="2"
              />
              <text
                x="0"
                y="5"
                fill={C.cyanPrimary}
                fontFamily="monospace"
                fontSize="15"
                fontWeight="700"
                textAnchor="middle"
              >
                s3:GetObject
              </text>
            </g>
          )}
        </g>
      )}

      {/* Re-connected Authorization Line to Successor (Frames 345 - 500) */}
      {f >= 345 && f < 500 && (
        <g>
          <path
            d={`M 390 ${roleY} L ${390 + (1355 - 390) * lineProgress2} ${roleY}`}
            stroke={C.cyanPrimary}
            strokeWidth="4"
            strokeLinecap="round"
          />
          {/* Action chip */}
          <g transform="translate(740, 500)">
            <rect
              x="-85"
              y="-20"
              width="170"
              height="40"
              rx="20"
              fill="#082333"
              stroke={C.cyanPrimary}
              strokeWidth="2"
            />
            <text
              x="0"
              y="5"
              fill={C.cyanPrimary}
              fontFamily="monospace"
              fontSize="15"
              fontWeight="700"
              textAnchor="middle"
            >
              s3:GetObject
            </text>
          </g>

          {/* Compact Authorization Check Result Node (✓) positioned cleanly above connector entrance */}
          {checkBadgeAppear > 0 && (
            <g transform="translate(1120, 440)" opacity={checkBadgeAppear}>
              <rect x="-140" y="-18" width="280" height="36" rx="18" fill="#062e24" stroke={C.emeraldPrimary} strokeWidth="2" />
              <circle cx="-110" cy="0" r="10" fill={C.emeraldPrimary} />
              <text x="-110" y="4" fill="#022c22" fontFamily="sans-serif" fontSize="12" fontWeight="900" textAnchor="middle">✓</text>
              <text
                x="15"
                y="5"
                fill={C.emeraldPrimary}
                fontFamily="system-ui, -apple-system, sans-serif"
                fontSize="12"
                fontWeight="800"
                letterSpacing="1.2"
                textAnchor="middle"
              >
                AUTHORIZATION: {status}
              </text>
            </g>
          )}
        </g>
      )}

      {/* ==================================================== */}
      {/* 5. THE S3 BUCKET HERO OBJECT (Continuous Single Hero)*/}
      {/* ==================================================== */}
      {bucketOpacity > 0 && (
        <S3BucketHero
          x={bucketX}
          y={bucketY}
          scale={bucketScale}
          opacity={bucketOpacity}
          label={isMigrated ? 'data' : 'invoice_data'}
          sublabel={isMigrated ? 'SUCCESSOR · S3 BUCKET' : 'S3 BUCKET · CLOUD STORAGE'}
          isNew={isMigrated}
          highlightGlow={f >= 385 && f < 500 ? 1 : 0}
        />
      )}

      {/* ==================================================== */}
      {/* 6. S3 RESOURCE OBLIGATIONS (17 - 19s, Unevaluated) */}
      {/* ==================================================== */}
      {obligationsAppear > 0 && (
        <g transform="translate(860, 300)" opacity={obligationsAppear}>
          {/* Card Frame */}
          <rect
            x="0"
            y="0"
            width="800"
            height="400"
            rx="24"
            fill="#0b1424"
            stroke="#334155"
            strokeWidth="2.5"
          />

          {/* Header */}
          <g transform="translate(45, 50)">
            <text
              x="0"
              y="0"
              fill={C.textPrimary}
              fontFamily="system-ui, -apple-system, sans-serif"
              fontSize="24"
              fontWeight="800"
            >
              S3 RESOURCE OBLIGATIONS
            </text>
            <text
              x="0"
              y="28"
              fill={C.textSecondary}
              fontFamily="system-ui, -apple-system, sans-serif"
              fontSize="14"
            >
              Security obligations evaluated outside the resource continuity slice
            </text>
          </g>

          {/* Three Obligation Rows (Explicitly UNKNOWN / NOT VERIFIED) */}
          {[
            {label: 'Encryption at rest (SSE-KMS)', key: 'enc'},
            {label: 'Block Public Access (BPA)', key: 'bpa'},
            {label: 'Server access logging', key: 'log'},
          ].map((item, idx) => (
            <g key={item.key} transform={`translate(45, ${136 + idx * 64})`}>
              <line x1="0" y1="-8" x2="710" y2="-8" stroke="#1e293b" strokeWidth="1" />
              <text
                x="0"
                y="24"
                fill={C.textPrimary}
                fontFamily="system-ui, -apple-system, sans-serif"
                fontSize="17"
                fontWeight="500"
              >
                {item.label}
              </text>

              {/* UNKNOWN Badge (Amber, clearly unevaluated) */}
              <g transform="translate(570, 2)">
                <rect
                  x="0"
                  y="0"
                  width="135"
                  height="34"
                  rx="17"
                  fill={C.amberBg}
                  stroke={C.amberPrimary}
                  strokeWidth="1.8"
                />
                <circle cx="22" cy="17" r="4.5" fill={C.amberPrimary} />
                <text
                  x="72"
                  y="22"
                  fill={C.amberPrimary}
                  fontFamily="system-ui, -apple-system, sans-serif"
                  fontSize="13"
                  fontWeight="800"
                  letterSpacing="1"
                  textAnchor="middle"
                >
                  UNKNOWN
                </text>
              </g>
            </g>
          ))}

          {/* Subtitle Warning Banner */}
          <g transform="translate(45, 342)">
            <rect x="0" y="0" width="710" height="32" rx="8" fill="#1e1828" stroke="#78350f" strokeWidth="1" />
            <text
              x="355"
              y="21"
              fill={C.amberPrimary}
              fontFamily="system-ui, -apple-system, sans-serif"
              fontSize="12"
              fontWeight="700"
              letterSpacing="0.8"
              textAnchor="middle"
            >
              OBLIGATIONS OUTSIDE CURRENT SABLE SLICE · LOCAL CONTROLLED MODEL
            </text>
          </g>
        </g>
      )}

      {/* ==================================================== */}
      {/* 7. FINAL SUPPORTED SABLE RESULT (19 - 20s)           */}
      {/* ==================================================== */}
      {resultCardAppear > 0 && (
        <g
          transform="translate(360, 220)"
          opacity={resultCardAppear}
        >
          {/* Card Backdrop with glow */}
          <rect
            x="0"
            y="0"
            width="1200"
            height="580"
            rx="32"
            fill="#0b1322"
            stroke={statusColor}
            strokeWidth="3.5"
            filter="url(#glowEffect)"
          />
          <rect
            x="0"
            y="0"
            width="1200"
            height="580"
            rx="32"
            fill="#09111e"
            stroke={statusColor}
            strokeWidth="2.5"
          />

          {/* Top Eyebrow */}
          <g transform="translate(600, 70)">
            <rect
              x="-190"
              y="-17"
              width="380"
              height="34"
              rx="17"
              fill="#131e33"
              stroke={C.violetPrimary}
              strokeWidth="1.8"
            />
            <text
              x="0"
              y="5"
              fill="#c7d2fe"
              fontFamily="system-ui, -apple-system, sans-serif"
              fontSize="13"
              fontWeight="800"
              letterSpacing="1.5"
              textAnchor="middle"
            >
              SUPPORTED SABLE MECHANISM
            </text>
          </g>

          {/* Center Main Conclusion */}
          <text
            x="600"
            y="155"
            fill={C.textSecondary}
            fontFamily="system-ui, -apple-system, sans-serif"
            fontSize="26"
            fontWeight="600"
            textAnchor="middle"
            letterSpacing="1"
          >
            AUTHORIZATION CONTINUITY
          </text>

          {/* Result Banner */}
          <g transform="translate(600, 245)">
            <rect
              x="-260"
              y="-48"
              width="520"
              height="96"
              rx="26"
              fill="#062e24"
              stroke={statusColor}
              strokeWidth="3.5"
            />
            <text
              x="0"
              y="18"
              fill={statusColor}
              fontFamily="system-ui, -apple-system, sans-serif"
              fontSize="56"
              fontWeight="900"
              letterSpacing="2.5"
              textAnchor="middle"
            >
              {status}
            </text>
          </g>

          {/* Evidence Details Grid */}
          <g transform="translate(180, 370)">
            <line x1="0" y1="0" x2="840" y2="0" stroke="#1e293b" strokeWidth="1.5" />

            <g transform="translate(0, 42)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, -apple-system, sans-serif" fontSize="13" fontWeight="600">
                SUCCESSOR CORRESPONDENCE
              </text>
              <text x="0" y="28" fill={C.textPrimary} fontFamily="monospace" fontSize="17" fontWeight="700">
                {successorName}
              </text>
            </g>

            <g transform="translate(480, 42)">
              <text x="0" y="0" fill={C.textMuted} fontFamily="system-ui, -apple-system, sans-serif" fontSize="13" fontWeight="600">
                EVIDENCE RUN IDENTIFIER
              </text>
              <text x="0" y="28" fill={C.textPrimary} fontFamily="monospace" fontSize="17" fontWeight="700">
                {evidence.runId || 'c6f6239d62b4'} · Integrity Valid
              </text>
            </g>
          </g>

          {/* Final Truthfulness Disclaimer Footer */}
          <text
            x="600"
            y="525"
            fill={C.textMuted}
            fontFamily="system-ui, -apple-system, sans-serif"
            fontSize="14"
            fontWeight="500"
            textAnchor="middle"
          >
            Controlled local model · Stored ASENT evidence checked · No live external AWS execution claimed
          </text>
        </g>
      )}

      {/* ==================================================== */}
      {/* Bottom Progress Bar & Global Footer                  */}
      {/* ==================================================== */}
      <g transform="translate(90, 1020)">
        <text
          x="0"
          y="0"
          fill={C.textMuted}
          fontFamily="system-ui, -apple-system, sans-serif"
          fontSize="13"
          fontWeight="500"
        >
          LOCAL CONTROLLED VISUALIZATION · STORED EVIDENCE IS AUTHORITATIVE
        </text>

        {/* Progress track */}
        <rect x="0" y="16" width="1740" height="4" rx="2" fill="#1e293b" />
        <rect
          x="0"
          y="16"
          width={(1740 * f) / SABLE_FRAMES}
          height="4"
          rx="2"
          fill={C.violetPrimary}
        />
      </g>
    </svg>
  );
};
