import { NavLink } from "react-router-dom"
import { motion } from "framer-motion"
import {
  LayoutDashboard, AlertTriangle, TrendingUp,
  Lightbulb, FileText, MessageCircle, Leaf,
} from "lucide-react"

const NAV = [
  { path: "/",          label: "Fleet Overview",    icon: LayoutDashboard, color: "#3b82f6" },
  { path: "/anomaly",   label: "Anomaly Monitor",   icon: AlertTriangle,   color: "#ef4444" },
  { path: "/trends",    label: "Trend Analysis",    icon: TrendingUp,      color: "#10b981" },
  { path: "/reduction", label: "Reduction Advisor", icon: Lightbulb,       color: "#f59e0b" },
  { path: "/esg",       label: "ESG Report",        icon: FileText,        color: "#6366f1" },
  { path: "/chat",      label: "Ask LORRI",         icon: MessageCircle,   color: "#06b6d4" },
]

export default function Sidebar() {
  return (
    <motion.aside
      initial={{ x: -280 }}
      animate={{ x: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      style={{
        width: 260, minHeight: "100vh",
        background: "#040d1f",
        borderRight: "1px solid rgba(59,130,246,0.12)",
        display: "flex", flexDirection: "column",
        position: "fixed", left: 0, top: 0, zIndex: 100,
      }}
    >
      {/* Logo */}
      <div style={{ padding: "28px 24px 20px", borderBottom: "1px solid rgba(59,130,246,0.1)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "linear-gradient(135deg,#1e40af,#3b82f6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 0 20px rgba(59,130,246,0.4)",
          }}>
            <Leaf size={18} color="white" />
          </div>
          <div>
            <div style={{ color: "#e2e8f0", fontWeight: 700, fontSize: 16 }}>LORRI</div>
            <div style={{ color: "#3b82f6", fontSize: 11, fontWeight: 500 }}>Carbon Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "16px 12px", flex: 1 }}>
        <p style={{ color: "#334155", fontSize: 11, fontWeight: 600,
          padding: "0 12px 8px", letterSpacing: "0.1em" }}>
          NAVIGATION
        </p>
        {NAV.map(({ path, label, icon: Icon, color }) => (
          <NavLink key={path} to={path} end={path === "/"} style={{ textDecoration: "none" }}>
            {({ isActive }) => (
              <motion.div
                whileHover={{ x: 4 }}
                style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "11px 14px", borderRadius: 10, marginBottom: 4,
                  background: isActive ? `${color}18` : "transparent",
                  border: isActive ? `1px solid ${color}30` : "1px solid transparent",
                  cursor: "pointer", transition: "all 0.2s ease",
                }}
              >
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  background: isActive ? `${color}25` : "rgba(255,255,255,0.04)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <Icon size={16} color={isActive ? color : "#475569"} />
                </div>
                <span style={{
                  fontSize: 14, fontWeight: isActive ? 600 : 400,
                  color: isActive ? "#e2e8f0" : "#475569",
                }}>
                  {label}
                </span>
                {isActive && (
                  <motion.div
                    layoutId="activeIndicator"
                    style={{
                      marginLeft: "auto", width: 6, height: 6,
                      borderRadius: "50%", background: color,
                      boxShadow: `0 0 8px ${color}`,
                    }}
                  />
                )}
              </motion.div>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: 16, borderTop: "1px solid rgba(59,130,246,0.1)" }}>
        <div style={{
          background: "rgba(59,130,246,0.06)",
          border: "1px solid rgba(59,130,246,0.12)",
          borderRadius: 10, padding: "12px 14px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <div style={{
              width: 8, height: 8, borderRadius: "50%",
              background: "#10b981",
              boxShadow: "0 0 8px #10b981",
              animation: "pulse-dot 1.5s ease-in-out infinite",
            }} />
            <span style={{ color: "#10b981", fontSize: 12, fontWeight: 600 }}>
              Agents Online
            </span>
          </div>
          <p style={{ color: "#334155", fontSize: 11 }}>Groq LLM · llama-3.3-70b</p>
        </div>
      </div>
    </motion.aside>
  )
}