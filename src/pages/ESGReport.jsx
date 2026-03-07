import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, LineChart, Line, ReferenceLine
} from "recharts"
import axios from "axios"
import TopBar from "../components/Layout/TopBar"
import GlassCard from "../components/shared/GlassCard"
import KPICard from "../components/shared/KPICard"
import LoadingSpinner from "../components/shared/LoadingSpinner"
import { FileText, Leaf, Target, Award } from "lucide-react"

const COLORS = ["#3b82f6","#10b981","#f59e0b","#6366f1","#ef4444","#8b5cf6","#06b6d4","#ec4899"]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: "rgba(4,13,31,0.95)",
      border: "1px solid rgba(59,130,246,0.3)",
      borderRadius: 10, padding: "10px 14px",
    }}>
      <p style={{ color: "#94a3b8", fontSize: 12, marginBottom: 4 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color, fontSize: 13, fontWeight: 600 }}>
          {p.name}: {typeof p.value === "number" ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  )
}

export default function ESGReport() {
  const [scope3,    setScope3]    = useState(null)
  const [breakdown, setBreakdown] = useState(null)
  const [targets,   setTargets]   = useState(null)
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    Promise.all([
      axios.get("/api/esg/scope3"),
      axios.get("/api/esg/breakdown"),
      axios.get("/api/esg/targets"),
    ]).then(([s, b, t]) => {
      setScope3(s.data)
      setBreakdown(b.data)
      setTargets(t.data)
      setLoading(false)
    })
  }, [])

  if (loading) return (
    <div style={{ marginLeft: 260 }}>
      <TopBar title="ESG Report" />
      <LoadingSpinner text="Generating ESG report..." />
    </div>
  )

  const vehicleData = breakdown?.by_vehicle_type?.map(v => ({
    name:  v.vehicle_type?.replace(/_/g, " "),
    co2:   v.co2_tonnes,
    share: v.share_pct,
  })) || []

  const targetData = targets?.yearly_targets?.filter(t => t.year >= 2022).map(t => ({
    year:    t.year.toString(),
    target:  t.target_tonnes,
    actual:  t.actual_tonnes,
    onTrack: t.on_track,
  })) || []

  return (
    <div style={{ marginLeft: 260, minHeight: "100vh" }}>
      <TopBar title="ESG Report" subtitle="GHG Protocol Scope 3 · Science-Based Targets · Paris Agreement" />
      <div style={{ padding: "28px 28px 40px" }}>

        {/* Header Badge */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            display: "inline-flex", alignItems: "center", gap: 8,
            background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)",
            borderRadius: 20, padding: "6px 16px", marginBottom: 20,
          }}
        >
          <Award size={14} color="#10b981" />
          <span style={{ color: "#10b981", fontSize: 13, fontWeight: 600 }}>
            GHG Protocol · Scope 3 Category 4 · Reporting Year 2024
          </span>
        </motion.div>

        {/* KPIs */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 }}>
          <KPICard
            title="TTW Emissions"
            value={scope3?.total_co2_ttw_tonnes?.toLocaleString()}
            unit="tonnes CO₂"
            subtitle="Tank-to-Wheel"
            icon={Leaf} color="green" delay={0}
          />
          <KPICard
            title="WTW Emissions"
            value={scope3?.total_co2_wtw_tonnes?.toLocaleString()}
            unit="tonnes CO₂e"
            subtitle={`×${scope3?.wtw_uplift_factor} WTW uplift`}
            icon={Leaf} color="blue" delay={0.1}
          />
          <KPICard
            title="Carbon Intensity"
            value={scope3?.carbon_intensity_g_tkm?.toFixed(1)}
            unit="g/tkm"
            subtitle="Operational intensity"
            icon={Target} color="indigo" delay={0.2}
          />
          <KPICard
            title="2030 Target"
            value={targets?.target_2030_tonnes?.toLocaleString()}
            unit="tonnes"
            subtitle={`-${targets?.target_reduction_pct}% from baseline`}
            icon={FileText} color="amber" delay={0.3}
          />
        </div>

        {/* Rows */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

          {/* Vehicle Type Breakdown */}
          <GlassCard title="CO₂ by Vehicle Type (tonnes)" delay={0.3}>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={vehicleData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.08)" />
                <XAxis dataKey="name" stroke="#334155" tick={{ fill: "#64748b", fontSize: 9 }} angle={-25} textAnchor="end" height={60} />
                <YAxis stroke="#334155" tick={{ fill: "#64748b", fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="co2" name="CO₂ (tonnes)" radius={[4, 4, 0, 0]}>
                  {vehicleData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </GlassCard>

          {/* Year-by-Year Targets */}
          <GlassCard title="Science-Based Target Pathway (to 2030)" delay={0.4}>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={targetData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.08)" />
                <XAxis dataKey="year" stroke="#334155" tick={{ fill: "#64748b", fontSize: 12 }} />
                <YAxis stroke="#334155" tick={{ fill: "#64748b", fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="target" stroke="#3b82f6" strokeWidth={2}
                  strokeDasharray="6 3" name="Target (t)" dot={{ fill: "#3b82f6", r: 4 }} />
                <Line type="monotone" dataKey="actual" stroke="#10b981" strokeWidth={2.5}
                  name="Actual (t)" dot={{ fill: "#10b981", r: 5 }}
                  connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
            <div style={{ display: "flex", gap: 16, marginTop: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 20, height: 2, background: "#3b82f6", borderRadius: 1, borderTop: "2px dashed #3b82f6" }} />
                <span style={{ color: "#64748b", fontSize: 12 }}>Target path</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 20, height: 2, background: "#10b981", borderRadius: 1 }} />
                <span style={{ color: "#64748b", fontSize: 12 }}>Actual</span>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Compliance Table */}
        <GlassCard title="Year-by-Year Compliance Status" delay={0.6}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Year","Target (tonnes)","Actual (tonnes)","Gap","Status"].map(h => (
                    <th key={h} style={{
                      textAlign: "left", padding: "10px 16px",
                      color: "#64748b", fontSize: 12, fontWeight: 600,
                      borderBottom: "1px solid rgba(59,130,246,0.1)",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {targetData.map((t, i) => {
                  const gap = t.actual ? (t.actual - t.target).toFixed(0) : null
                  return (
                    <motion.tr
                      key={t.year}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.7 + i * 0.05 }}
                      whileHover={{ background: "rgba(59,130,246,0.04)" }}
                      style={{ borderBottom: "1px solid rgba(59,130,246,0.06)" }}
                    >
                      <td style={{ padding: "12px 16px", color: "#3b82f6", fontWeight: 600 }}>{t.year}</td>
                      <td style={{ padding: "12px 16px", color: "#e2e8f0" }}>{t.target?.toLocaleString()}</td>
                      <td style={{ padding: "12px 16px", color: t.actual ? "#e2e8f0" : "#475569" }}>
                        {t.actual?.toLocaleString() || "—"}
                      </td>
                      <td style={{ padding: "12px 16px", color: gap > 0 ? "#ef4444" : gap < 0 ? "#10b981" : "#64748b", fontWeight: 600 }}>
                        {gap ? (gap > 0 ? `+${gap}` : gap) : "—"}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        {t.actual ? (
                          <span style={{
                            padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600,
                            background: t.onTrack ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
                            color: t.onTrack ? "#10b981" : "#ef4444",
                          }}>
                            {t.onTrack ? "✅ On Track" : "⚠️ Off Track"}
                          </span>
                        ) : (
                          <span style={{ color: "#475569", fontSize: 12 }}>Projected</span>
                        )}
                      </td>
                    </motion.tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}