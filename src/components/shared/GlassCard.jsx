import { motion } from "framer-motion"

export default function GlassCard({ children, title, delay = 0, style = {} }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5 }}
      style={{
        background:     "rgba(13,25,55,0.7)",
        backdropFilter: "blur(12px)",
        border:         "1px solid rgba(59,130,246,0.15)",
        borderRadius:   "16px",
        padding:        "24px",
        ...style,
      }}
    >
      {title && (
        <h3 style={{
          color: "#e2e8f0", fontSize: "15px",
          fontWeight: 600, marginBottom: 20,
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span style={{
            width: 3, height: 18, background: "#3b82f6",
            borderRadius: 2, display: "inline-block",
          }} />
          {title}
        </h3>
      )}
      {children}
    </motion.div>
  )
}