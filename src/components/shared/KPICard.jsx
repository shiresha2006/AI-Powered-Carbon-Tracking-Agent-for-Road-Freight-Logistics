import { motion } from "framer-motion"

export default function KPICard({
  title, value, unit, subtitle,
  icon: Icon, color = "blue",
  delay = 0, trend
}) {
  const colors = {
    blue:   { glow: "rgba(59,130,246,0.3)",  text: "#3b82f6", bg: "rgba(59,130,246,0.1)"  },
    green:  { glow: "rgba(16,185,129,0.3)",  text: "#10b981", bg: "rgba(16,185,129,0.1)"  },
    red:    { glow: "rgba(239,68,68,0.3)",   text: "#ef4444", bg: "rgba(239,68,68,0.1)"   },
    amber:  { glow: "rgba(245,158,11,0.3)",  text: "#f59e0b", bg: "rgba(245,158,11,0.1)"  },
    indigo: { glow: "rgba(99,102,241,0.3)",  text: "#6366f1", bg: "rgba(99,102,241,0.1)"  },
    cyan:   { glow: "rgba(6,182,212,0.3)",   text: "#06b6d4", bg: "rgba(6,182,212,0.1)"   },
  }
  const c = colors[color] || colors.blue

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5 }}
      whileHover={{ y: -6, boxShadow: `0 20px 40px ${c.glow}` }}
      style={{
        background:   "rgba(13,25,55,0.7)",
        backdropFilter: "blur(12px)",
        border:       "1px solid rgba(59,130,246,0.15)",
        borderRadius: "16px",
        padding:      "24px",
        cursor:       "default",
        transition:   "all 0.3s ease",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <p style={{ color: "#64748b", fontSize: "13px", fontWeight: 500, marginBottom: 8 }}>
            {title}
          </p>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.3 }}
              style={{ fontSize: "28px", fontWeight: 700, color: c.text }}
            >
              {value}
            </motion.span>
            {unit && (
              <span style={{ color: "#64748b", fontSize: "13px" }}>{unit}</span>
            )}
          </div>
          {subtitle && (
            <p style={{ color: "#94a3b8", fontSize: "12px", marginTop: 6 }}>
              {subtitle}
            </p>
          )}
          {trend && (
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 4,
              marginTop: 8, padding: "2px 8px", borderRadius: 20,
              background: trend > 0 ? "rgba(239,68,68,0.1)" : "rgba(16,185,129,0.1)",
              color: trend > 0 ? "#ef4444" : "#10b981",
              fontSize: "12px", fontWeight: 600,
            }}>
              {trend > 0 ? "↑" : "↓"} {Math.abs(trend)}%
            </div>
          )}
        </div>
        {Icon && (
          <div style={{
            width: 48, height: 48, borderRadius: 12,
            background: c.bg, display: "flex",
            alignItems: "center", justifyContent: "center",
          }}>
            <Icon size={22} color={c.text} />
          </div>
        )}
      </div>
    </motion.div>
  )
}