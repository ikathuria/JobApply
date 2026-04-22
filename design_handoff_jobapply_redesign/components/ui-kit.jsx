// Shared UI components — exports to window
const { useState, useEffect, useRef, useContext, createContext } = React;

// ── Theme context ──────────────────────────────────────────────────────────────
const ThemeCtx = createContext({ dark: true });

const DARK = {
  bg:       "#0C0C14",
  surface:  "#13131E",
  card:     "#1A1A28",
  border:   "#252538",
  text:     "#EEEEF8",
  muted:    "#7878A0",
  accent:   "#6366F1",
  accentBg: "rgba(99,102,241,0.12)",
  success:  "#22C55E",
  warning:  "#F59E0B",
  danger:   "#EF4444",
  pink:     "#EC4899",
};
const LIGHT = {
  bg:       "#F4F4FA",
  surface:  "#FFFFFF",
  card:     "#FAFAFA",
  border:   "#E2E2EE",
  text:     "#1A1A2E",
  muted:    "#7878A0",
  accent:   "#4F52D9",
  accentBg: "rgba(79,82,217,0.09)",
  success:  "#16A34A",
  warning:  "#D97706",
  danger:   "#DC2626",
  pink:     "#DB2777",
};

// ── Score bar ─────────────────────────────────────────────────────────────────
function ScoreBar({ score, height = 4, showLabel = false }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  const pct = Math.round(score * 100);
  const color = score >= 0.75 ? T.success : score >= 0.55 ? T.warning : T.danger;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height, borderRadius: height, background: dark ? "#252538" : "#E2E2EE", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: height, transition: "width 0.4s ease" }} />
      </div>
      {showLabel && <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color, fontWeight: 700, minWidth: 32 }}>{pct}%</span>}
    </div>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status, size = "sm" }) {
  const meta = window.STATUS_META[status] || { label: status, color: "#888", bg: "#88888820" };
  const pad = size === "sm" ? "2px 8px" : "3px 12px";
  const fs  = size === "sm" ? 11 : 12;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: pad, borderRadius: 20, fontSize: fs, fontWeight: 700,
      color: meta.color, background: meta.bg, letterSpacing: "0.03em",
      border: `1px solid ${meta.color}30`,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: meta.color, flexShrink: 0 }} />
      {meta.label}
    </span>
  );
}

// ── Button ─────────────────────────────────────────────────────────────────────
function Btn({ children, variant = "primary", onClick, style = {}, disabled = false, size = "md" }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  const [hov, setHov] = useState(false);
  const baseStyle = {
    display: "inline-flex", alignItems: "center", justifyContent: "center",
    gap: 6, border: "none", cursor: disabled ? "not-allowed" : "pointer",
    fontFamily: "DM Sans, sans-serif", fontWeight: 600,
    borderRadius: 8, transition: "all 0.15s ease",
    fontSize: size === "sm" ? 12 : size === "lg" ? 15 : 13,
    padding: size === "sm" ? "5px 12px" : size === "lg" ? "13px 24px" : "8px 16px",
    opacity: disabled ? 0.5 : 1,
  };
  const variants = {
    primary:   { background: hov ? "#7577F5" : T.accent, color: "#fff" },
    secondary: { background: hov ? (dark ? "#2A2A3E" : "#E8E8F4") : (dark ? "#1E1E30" : "#ECECF8"), color: T.text, border: `1px solid ${T.border}` },
    ghost:     { background: hov ? T.accentBg : "transparent", color: T.muted },
    danger:    { background: hov ? "#F87171" : T.danger, color: "#fff" },
    success:   { background: hov ? "#34D399" : T.success, color: "#fff" },
  };
  return (
    <button style={{ ...baseStyle, ...variants[variant], ...style }}
      onClick={onClick} disabled={disabled}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}>
      {children}
    </button>
  );
}

// ── Pill chip ─────────────────────────────────────────────────────────────────
function Chip({ children, active, onClick, color }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "inline-flex", alignItems: "center", gap: 5, padding: "5px 14px",
        borderRadius: 20, fontSize: 12, fontWeight: 700, cursor: "pointer", border: "none",
        transition: "all 0.15s",
        background: active ? (color || T.accent) : (hov ? T.accentBg : (dark ? "#1E1E30" : "#ECECF8")),
        color: active ? "#fff" : T.muted,
        letterSpacing: "0.02em",
      }}>
      {children}
    </button>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────────
function Card({ children, style = {}, onClick, noPad = false }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  const [hov, setHov] = useState(false);
  return (
    <div onClick={onClick}
      onMouseEnter={() => onClick && setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        background: T.card, border: `1px solid ${hov && onClick ? T.accent + "60" : T.border}`,
        borderRadius: 12, padding: noPad ? 0 : "16px 20px",
        cursor: onClick ? "pointer" : "default",
        transition: "border-color 0.15s, box-shadow 0.15s",
        boxShadow: hov && onClick ? `0 0 0 3px ${T.accent}18` : dark ? "none" : "0 1px 4px rgba(0,0,0,0.06)",
        ...style
      }}>
      {children}
    </div>
  );
}

// ── Input ─────────────────────────────────────────────────────────────────────
function Input({ value, onChange, placeholder, style = {}, icon }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  return (
    <div style={{ position: "relative", ...style }}>
      {icon && <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: T.muted, fontSize: 14, pointerEvents: "none" }}>{icon}</span>}
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        style={{
          width: "100%", boxSizing: "border-box",
          padding: icon ? "9px 12px 9px 36px" : "9px 12px",
          background: dark ? "#1A1A28" : "#FAFAFA",
          border: `1px solid ${T.border}`,
          borderRadius: 8, color: T.text, fontSize: 13,
          fontFamily: "DM Sans, sans-serif", outline: "none",
        }}
      />
    </div>
  );
}

// ── Textarea ──────────────────────────────────────────────────────────────────
function Textarea({ value, onChange, placeholder, rows = 4, style = {} }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  return (
    <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={rows}
      style={{
        width: "100%", boxSizing: "border-box", padding: "9px 12px",
        background: dark ? "#1A1A28" : "#FAFAFA",
        border: `1px solid ${T.border}`,
        borderRadius: 8, color: T.text, fontSize: 13,
        fontFamily: "DM Sans, sans-serif", outline: "none", resize: "vertical",
        ...style
      }}
    />
  );
}

// ── Divider ───────────────────────────────────────────────────────────────────
function Divider({ style = {} }) {
  const { dark } = useContext(ThemeCtx);
  return <div style={{ height: 1, background: dark ? "#252538" : "#E2E2EE", margin: "12px 0", ...style }} />;
}

// ── Tag ───────────────────────────────────────────────────────────────────────
function Tag({ children, style = {} }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  return (
    <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 5, fontSize: 11, fontWeight: 600, fontFamily: "JetBrains Mono, monospace", background: dark ? "#1E1E30" : "#ECECF8", color: T.muted, ...style }}>
      {children}
    </span>
  );
}

// ── Stat box ──────────────────────────────────────────────────────────────────
function StatBox({ label, value, color, sub }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <div style={{ fontSize: 24, fontWeight: 800, color: color || T.text, letterSpacing: "-0.03em", lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: "uppercase", letterSpacing: "0.07em" }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: T.muted }}>{sub}</div>}
    </div>
  );
}

Object.assign(window, { ThemeCtx, DARK, LIGHT, ScoreBar, StatusBadge, Btn, Chip, Card, Input, Textarea, Divider, Tag, StatBox });
