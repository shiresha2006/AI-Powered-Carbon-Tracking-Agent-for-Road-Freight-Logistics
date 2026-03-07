import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import axios from "axios"
import TopBar from "../components/Layout/TopBar"
import GlassCard from "../components/shared/GlassCard"
import LoadingSpinner from "../components/shared/LoadingSpinner"
import { AlertTriangle, Search, ChevronRight, Zap } from "lucide-react"

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

export default function AnomalyMonitor() {
  const [month,      setMonth]      = useState(10)
  const [year,       setYear]       = useState(2024)
  const [anomalies,  setAnomalies]  = useState(null)
  const [selected,   setSelected]   = useState(null)
  const [details,    setDetails]    = useState(null)
  const [rootCause,  setRootCause]  = useState(null)
  const [loading,    setLoading]    = useState(false)
  const [detLoading, setDetLoading] = useState(false)

  const scan = () => {
    setLoading(true)
    setSelected(null); setDetails(null); setRootCause(null)
    axios.get(`/api/anomaly/scan?month=${month}&year=${year}&top_n=15`)
      .then(r => { setAnomalies(r.data); setLoading(false) })
  }

  const inspect = (shipment) => {
    setSelected(shipment)
    setDetLoading(true)
    Promise.all([
      axios.get(`/api/anomaly/shipment/${shipment.shipment_id}`),
      axios.get(`/api/anomaly/root-cause/${shipment.shipment_id}`),
    ]).then(([d, r]) => {
      setDetails(d.data)
      setRootCause(r.data)
      setDetLoading(false)
    })
  }

  useEffect(() => { scan() }, [])

  const impactColor = i => i === "CRITICAL" ? "#ef4444" : i === "HIGH" ? "#f59e0b" : i === "MEDIUM" ? "#3b82f6" : "#10b981"
  const severityColor = r => r > 3 ? "#ef4444" : r > 2 ? "#f59e0b" : "#3b82f6"

  return (
    <div style={{ marginLeft: 260, minHeight: "100vh" }}>
      <TopBar title="Anomaly Monitor" subtitle="Detect and investigate emission anomalies" />
      <div style={{ padding: "28px 28px 40px" }}>

        {/* Controls */}
        <GlassCard delay={0} style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
            <div>
              <label style={{ color: "#64748b", fontSize: 12, display: "block", marginBottom: 6 }}>Month</label>
              <select
                value={month}
                onChange={e => setMonth(parseInt(e.target.value))}
                style={{
                  background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)",
                  color: "#e2e8f0", borderRadius: 8, padding: "8px 16px", fontSize: 14, cursor: "pointer",
                }}
              >
                {MONTHS.map((m, i) => (
                  <option key={i} value={i + 1} style={{ background: "#040d1f" }}>{m}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ color: "#64748b", fontSize: 12, display: "block", marginBottom: 6 }}>Year</label>
              <select
                value={year}
                onChange={e => setYear(parseInt(e.target.value))}
                style={{
                  background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)",
                  color: "#e2e8f0", borderRadius: 8, padding: "8px 16px", fontSize: 14, cursor: "pointer",
                }}
              >
                {[2022, 2023, 2024].map(y => (
                  <option key={y} value={y} style={{ background: "#040d1f" }}>{y}</option>
                ))}
              </select>
            </div>
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={scan}
              style={{
                marginTop: 20, display: "flex", alignItems: "center", gap: 8,
                background: "linear-gradient(135deg,#1e40af,#3b82f6)",
                border: "none", color: "white", borderRadius: 10,
                padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer",
                boxShadow: "0 4px 20px rgba(59,130,246,0.3)",
              }}
            >
              <Search size={16} /> Scan Fleet
            </motion.button>

            {anomalies && (
              <div style={{ marginTop: 20, display: "flex", gap: 20 }}>
                <div style={{ textAlign: "center" }}>
                  <div style={{ color: "#ef4444", fontSize: 22, fontWeight: 700 }}>
                    {anomalies.anomaly_count}
                  </div>
                  <div style={{ color: "#64748b", fontSize: 12 }}>Anomalies</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ color: "#f59e0b", fontSize: 22, fontWeight: 700 }}>
                    {anomalies.anomaly_rate_pct}%
                  </div>
                  <div style={{ color: "#64748b", fontSize: 12 }}>Rate</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ color: "#3b82f6", fontSize: 22, fontWeight: 700 }}>
                    {anomalies.total_shipments}
                  </div>
                  <div style={{ color: "#64748b", fontSize: 12 }}>Total</div>
                </div>
              </div>
            )}
          </div>
        </GlassCard>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

          {/* Anomaly List */}
          <GlassCard title={`Anomalous Shipments — ${MONTHS[month-1]} ${year}`} delay={0.1}>
            {loading ? <LoadingSpinner text="Scanning fleet..." /> : (
              <div style={{ maxHeight: 520, overflowY: "auto" }}>
                {anomalies?.top_anomalies?.map((a, i) => (
                  <motion.div
                    key={a.shipment_id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    whileHover={{ background: "rgba(59,130,246,0.08)", x: 4 }}
                    onClick={() => inspect(a)}
                    style={{
                      padding: "14px 12px", borderRadius: 10, cursor: "pointer",
                      border: selected?.shipment_id === a.shipment_id
                        ? "1px solid rgba(59,130,246,0.4)"
                        : "1px solid transparent",
                      background: selected?.shipment_id === a.shipment_id
                        ? "rgba(59,130,246,0.08)" : "transparent",
                      marginBottom: 4, display: "flex",
                      justifyContent: "space-between", alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <span style={{
                          width: 8, height: 8, borderRadius: "50%",
                          background: severityColor(a.severity_ratio),
                          display: "inline-block",
                          boxShadow: `0 0 6px ${severityColor(a.severity_ratio)}`,
                        }} />
                        <span style={{ color: "#3b82f6", fontSize: 13, fontWeight: 600 }}>
                          {a.shipment_id}
                        </span>
                        <span style={{ color: "#64748b", fontSize: 11 }}>
                          {new Date(a.shipment_date).toLocaleDateString()}
                        </span>
                      </div>
                      <div style={{ color: "#e2e8f0", fontSize: 13 }}>
                        {a.origin} → {a.destination}
                      </div>
                      <div style={{ color: "#64748b", fontSize: 12, marginTop: 2 }}>
                        {a.carrier_name} · {a.vehicle_type?.replace(/_/g, " ")}
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ color: "#f59e0b", fontSize: 14, fontWeight: 700 }}>
                        {a.co2_kg?.toLocaleString()} kg
                      </div>
                      <div style={{
                        fontSize: 11, fontWeight: 600,
                        color: severityColor(a.severity_ratio),
                      }}>
                        {a.severity_ratio}x avg
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </GlassCard>

          {/* Detail Panel */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <AnimatePresence mode="wait">
              {!selected ? (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{
                    background: "rgba(13,25,55,0.7)",
                    backdropFilter: "blur(12px)",
                    border: "1px solid rgba(59,130,246,0.1)",
                    borderRadius: 16, padding: 40,
                    display: "flex", flexDirection: "column",
                    alignItems: "center", justifyContent: "center",
                    minHeight: 200, gap: 12,
                  }}
                >
                  <AlertTriangle size={40} color="rgba(59,130,246,0.3)" />
                  <p style={{ color: "#475569", fontSize: 14 }}>
                    Click a shipment to investigate
                  </p>
                </motion.div>
              ) : (
                <motion.div key={selected.shipment_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  {detLoading ? <LoadingSpinner text="Analyzing root cause..." /> : (
                    <>
                      {/* Shipment Details */}
                      <GlassCard title={`Shipment: ${selected.shipment_id}`} delay={0}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                          {details?.shipment && Object.entries({
                            "Route":    `${details.shipment.origin} → ${details.shipment.destination}`,
                            "CO₂":      `${details.shipment.co2_kg?.toLocaleString()} kg`,
                            "Vehicle":  details.shipment.vehicle_type?.replace(/_/g," "),
                            "Carrier":  details.shipment.carrier_name,
                            "Load":     `${details.shipment.load_utilization_pct?.toFixed(1)}%`,
                            "Veh Age":  `${details.shipment.vehicle_age_years?.toFixed(0)} yrs`,
                            "Fuel":     details.shipment.fuel_type?.toUpperCase(),
                            "Road":     details.shipment.road_type?.toUpperCase(),
                          }).map(([k, v]) => (
                            <div key={k} style={{
                              background: "rgba(59,130,246,0.05)",
                              borderRadius: 8, padding: "8px 12px",
                            }}>
                              <div style={{ color: "#64748b", fontSize: 11 }}>{k}</div>
                              <div style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>{v}</div>
                            </div>
                          ))}
                        </div>
                      </GlassCard>

                      {/* Root Causes */}
                      <GlassCard title="Root Cause Analysis" delay={0.1}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                          {rootCause?.root_causes?.map((c, i) => (
                            <motion.div
                              key={i}
                              initial={{ opacity: 0, x: 20 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: i * 0.1 }}
                              style={{
                                padding: "10px 14px", borderRadius: 10,
                                background: `${impactColor(c.impact)}12`,
                                border: `1px solid ${impactColor(c.impact)}30`,
                              }}
                            >
                              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                                <span style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>
                                  {c.factor}
                                </span>
                                <span style={{
                                  fontSize: 11, fontWeight: 700, padding: "2px 8px",
                                  borderRadius: 20, background: `${impactColor(c.impact)}20`,
                                  color: impactColor(c.impact),
                                }}>
                                  {c.impact}
                                </span>
                              </div>
                              <p style={{ color: "#64748b", fontSize: 12 }}>{c.detail}</p>
                              <p style={{ color: impactColor(c.impact), fontSize: 12, fontWeight: 600, marginTop: 2 }}>
                                Value: {c.value}
                              </p>
                            </motion.div>
                          ))}
                        </div>
                      </GlassCard>
                    </>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  )
}