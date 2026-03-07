import { motion } from "framer-motion"
import { Bell, Settings, User } from "lucide-react"

export default function TopBar({ title, subtitle }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        height: 64,
        background: "rgba(4,13,31,0.9)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(59,130,246,0.1)",
        display: "flex", alignItems: "center",
        justifyContent: "space-between",
        padding: "0 28px",
        position: "sticky", top: 0, zIndex: 50,
      }}
    >
      <div>
        <h1 style={{ color: "#e2e8f0", fontSize: 18, fontWeight: 700 }}>{title}</h1>
        {subtitle && <p style={{ color: "#64748b", fontSize: 12 }}>{subtitle}</p>}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {[Bell, Settings, User].map((Icon, i) => (
          <motion.button
            key={i}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            style={{
              width: 36, height: 36, borderRadius: 8,
              background: "rgba(59,130,246,0.08)",
              border: "1px solid rgba(59,130,246,0.15)",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: "pointer", color: "#64748b",
            }}
          >
            <Icon size={16} />
          </motion.button>
        ))}
      </div>
    </motion.header>
  )
}