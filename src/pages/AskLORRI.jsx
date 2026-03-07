import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import axios from "axios"
import TopBar from "../components/Layout/TopBar"
import { Send, Bot, User, Leaf, Zap } from "lucide-react"

const SUGGESTIONS = [
  "Give me a complete fleet emission overview for 2024",
  "Find anomalies in October 2024 and explain the worst one",
  "What are the top CO₂ reduction opportunities?",
  "Are we on track for our 30% reduction target?",
  "Generate our Scope 3 ESG report for 2024",
  "Which carrier has the worst emission performance?",
]

const agentColor = a => ({
  fleet_summary:     "#3b82f6",
  anomaly_monitor:   "#ef4444",
  trend_forecaster:  "#10b981",
  reduction_advisor: "#f59e0b",
  esg_report:        "#6366f1",
}[a] || "#3b82f6")

const agentLabel = a => ({
  fleet_summary:     "Fleet Agent",
  anomaly_monitor:   "Anomaly Agent",
  trend_forecaster:  "Trend Agent",
  reduction_advisor: "Reduction Agent",
  esg_report:        "ESG Agent",
}[a] || "LORRI Agent")

export default function AskLORRI() {
  const [messages, setMessages] = useState([{
    role: "assistant",
    content: "Hello! I'm LORRI, your Carbon Intelligence Agent. I can analyze fleet emissions, detect anomalies, identify reduction opportunities, and generate ESG reports. What would you like to know?",
    agent: "fleet_summary",
  }])
  const [input,   setInput]   = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const send = async (text = input) => {
    if (!text.trim() || loading) return
    const userMsg = { role: "user", content: text }
    setMessages(m => [...m, userMsg])
    setInput("")
    setLoading(true)

    try {
      const res = await axios.post("/api/chat/", { query: text })
      setMessages(m => [...m, {
        role:    "assistant",
        content: res.data.response,
        agent:   res.data.agent_used,
      }])
    } catch {
      setMessages(m => [...m, {
        role:    "assistant",
        content: "Sorry, I encountered an error. Please check the backend is running.",
        agent:   "fleet_summary",
      }])
    }
    setLoading(false)
  }

  return (
    <div style={{ marginLeft: 260, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <TopBar title="Ask LORRI" subtitle="AI-powered carbon intelligence · Groq · llama-3.3-70b" />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "0 28px 28px" }}>

        {/* Suggestions */}
        {messages.length === 1 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ padding: "20px 0 16px" }}
          >
            <p style={{ color: "#475569", fontSize: 13, marginBottom: 12 }}>
              Try asking:
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {SUGGESTIONS.map((s, i) => (
                <motion.button
                  key={i}
                  whileHover={{ scale: 1.02, borderColor: "rgba(59,130,246,0.5)" }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => send(s)}
                  style={{
                    background: "rgba(59,130,246,0.06)",
                    border: "1px solid rgba(59,130,246,0.15)",
                    borderRadius: 20, padding: "7px 14px",
                    color: "#94a3b8", fontSize: 12, cursor: "pointer",
                    transition: "all 0.2s ease",
                  }}
                >
                  {s}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: "auto", padding: "16px 0",
          display: "flex", flexDirection: "column", gap: 16,
          maxHeight: "calc(100vh - 260px)",
        }}>
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  display: "flex",
                  justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                  gap: 12, alignItems: "flex-start",
                }}
              >
                {msg.role === "assistant" && (
                  <div style={{
                    width: 36, height: 36, borderRadius: 10, flexShrink: 0,
                    background: `${agentColor(msg.agent)}20`,
                    border: `1px solid ${agentColor(msg.agent)}40`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <Bot size={18} color={agentColor(msg.agent)} />
                  </div>
                )}

                <div style={{ maxWidth: "72%" }}>
                  {msg.role === "assistant" && msg.agent && (
                    <div style={{
                      display: "flex", alignItems: "center", gap: 6, marginBottom: 6,
                    }}>
                      <span style={{
                        fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 20,
                        background: `${agentColor(msg.agent)}15`,
                        color: agentColor(msg.agent),
                      }}>
                        {agentLabel(msg.agent)}
                      </span>
                    </div>
                  )}
                  <div style={{
                    padding: "14px 18px", borderRadius: msg.role === "user" ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
                    background: msg.role === "user"
                      ? "linear-gradient(135deg,#1e40af,#3b82f6)"
                      : "rgba(13,25,55,0.8)",
                    border: msg.role === "user"
                      ? "none"
                      : `1px solid ${agentColor(msg.agent)}25`,
                    boxShadow: msg.role === "user"
                      ? "0 4px 20px rgba(59,130,246,0.3)"
                      : "none",
                  }}>
                    <p style={{
                      color: "#e2e8f0", fontSize: 14, lineHeight: 1.7,
                      whiteSpace: "pre-wrap", margin: 0,
                    }}>
                      {msg.content}
                    </p>
                  </div>
                </div>

                {msg.role === "user" && (
                  <div style={{
                    width: 36, height: 36, borderRadius: 10, flexShrink: 0,
                    background: "rgba(59,130,246,0.15)",
                    border: "1px solid rgba(59,130,246,0.3)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <User size={18} color="#3b82f6" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Loading indicator */}
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ display: "flex", alignItems: "center", gap: 12 }}
            >
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: "rgba(59,130,246,0.1)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Zap size={18} color="#3b82f6" />
              </div>
              <div style={{
                background: "rgba(13,25,55,0.8)",
                border: "1px solid rgba(59,130,246,0.2)",
                borderRadius: "4px 16px 16px 16px",
                padding: "14px 18px", display: "flex", gap: 6, alignItems: "center",
              }}>
                {[0, 1, 2].map(i => (
                  <motion.div
                    key={i}
                    animate={{ y: [-4, 0, -4] }}
                    transition={{ duration: 0.8, delay: i * 0.15, repeat: Infinity }}
                    style={{ width: 8, height: 8, borderRadius: "50%", background: "#3b82f6" }}
                  />
                ))}
                <span style={{ color: "#64748b", fontSize: 13, marginLeft: 4 }}>
                  LORRI is thinking...
                </span>
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{
          display: "flex", gap: 12, alignItems: "flex-end",
          background: "rgba(13,25,55,0.8)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(59,130,246,0.2)",
          borderRadius: 16, padding: "12px 16px",
          boxShadow: "0 0 30px rgba(59,130,246,0.1)",
        }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Ask LORRI anything about your fleet emissions..."
            rows={1}
            style={{
              flex: 1, background: "transparent", border: "none", outline: "none",
              color: "#e2e8f0", fontSize: 14, resize: "none",
              fontFamily: "inherit", lineHeight: 1.6, maxHeight: 120,
            }}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => send()}
            disabled={!input.trim() || loading}
            style={{
              width: 40, height: 40, borderRadius: 10, flexShrink: 0,
              background: input.trim() && !loading
                ? "linear-gradient(135deg,#1e40af,#3b82f6)"
                : "rgba(59,130,246,0.1)",
              border: "none", cursor: input.trim() && !loading ? "pointer" : "not-allowed",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: input.trim() ? "0 4px 20px rgba(59,130,246,0.3)" : "none",
            }}
          >
            <Send size={16} color={input.trim() && !loading ? "white" : "#475569"} />
          </motion.button>
        </div>
      </div>
    </div>
  )
}