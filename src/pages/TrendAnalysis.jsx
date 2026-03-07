import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine
} from "recharts"
import axios from "axios"
import TopBar from "../components/Layout/TopBar"
import GlassCard from "../components/shared/GlassCard"
import KPICard from "../components/shared/KPICard"
import LoadingSpinner from "../components/shared/LoadingSpinner"
import { TrendingUp, TrendingDown, Target, Calendar } from "lucide-react"

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

export default function TrendAnalysis() {
  const [monthly,    setMonthly]    = useState(null)
  const [compliance, setCompliance] = useState(null)
  const [laneTrend,  setLaneTrend]  = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [origin,     setOrigin]     = useState("Mumbai")
  const [dest,       setDest]       = useState("Delhi")

  useEffect(() => {
    Promise.all([
      axios.get("/api/trends/monthly?year=2024"),
      axios.get("/api/trends/compliance?target_annual_co2_tonnes=9334.69&year=2024"),
    ]).then(([m, c]) => {
      setMonthly(m.data)
      setCompliance(c.data)
      setLoading(false)
    })
  }, [])

  const fetchLane = () => {
    axios.get(`/api/trends/lane?origin=${origin}&destination=${dest}&period_days=365`)
      .then(r => setLaneTrend(r.data))
  }

  useEffect(() => { fetchLane() }, [])

  if (loading) return (
    <div style={{ marginLeft: 260 }}>
      <TopBar title="Trend Analysis" />
      <LoadingSpinner text="Loading trend data..." />
    </div>
  )

  const monthlyData = monthly?.monthly_data?.map(m => ({
    month:    `M${m.month}`,
    total:    Math.round(m.total_co2 / 1000),
    avg:      Math.round(m.avg_co2),
    mom:      m.mom_change_pct,
    anomaly:  parseFloat((m.anomaly_rate * 100).toFixed(2)),
  })) || []

  const laneData = laneTrend?.monthly_data?.map(m => ({
    period: m.month_year,
    avg_co2: Math.round(m.avg_co2),
    total:  Math.round(m.total_co2 / 1000),
  })) || []

  return (
    <div style={{ marginLeft: 260, minHeight: "100vh" }}>
      <TopBar title="Trend Analysis" subtitle="Emission trends, forecasts and target compliance" />
      <div style={{ padding: "28px 28px 40px" }}>

        {/* KPIs */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 }}>
          <KPICard
            title="Annual CO₂ (Projected)"
            value={compliance?.projected_annual_tonnes?.toLocaleString()}
            unit="tonnes"
            subtitle={compliance?.on_track ? "✅ On Track" : "⚠️ Off Track"}
            icon={TrendingUp}
            color={compliance?.on_track ? "green" : "red"}
            delay={0}
          />
          <KPICard
            title="Target 2030"
            value={compliance?.target_annual_co2_tonnes?.toLocaleString()}
            unit="tonnes"
            subtitle="30% reduction goal"
            icon={Target} color="indigo" delay={0.1}
          />
          <KPICard
            title="Gap to Target"
            value={Math.abs(compliance?.gap_tonnes || 0).toLocaleString()}
            unit="tonnes"
            subtitle={compliance?.on_track ? "Surplus" : "Deficit"}
            icon={compliance?.on_track ? TrendingDown : TrendingUp}
            color={compliance?.on_track ? "green" : "amber"}
            delay={0.2}
          />
          <KPICard
            title="Peak Month"
            value={monthly?.peak_month ? `Month ${monthly.peak_month}` : "—"}
            unit=""
            subtitle={`Lowest: Month ${monthly?.lowest_month}`}
            icon={Calendar} color="blue" delay={0.3}
          />
        </div>

        {/* Compliance Progress */}
        <GlassCard title="Target Compliance Progress" delay={0.2} style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ color: "#94a3b8", fontSize: 13 }}>
                {compliance?.actual_co2_tonnes_so_far?.toLocaleString()} tonnes actual
              </span>
              <span style={{ color: "#64748b", fontSize: 13 }}>
                Target: {compliance?.target_annual_co2_tonnes?.toLocaleString()} tonnes
              </span>
            </div>
            <div style={{ background: "rgba(59,130,246,0.1)", borderRadius: 8, height: 12, overflow: "hidden" }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{
                  width: `${Math.min(
                    (compliance?.projected_annual_tonnes / compliance?.target_annual_co2_tonnes) * 100,
                    100
                  )}%`
                }}
                transition={{ duration: 1.2, ease: "easeOut" }}
                style={{
                  height: "100%", borderRadius: 8,
                  background: compliance?.on_track
                    ? "linear-gradient(90deg,#10b981,#06b6d4)"
                    : "linear-gradient(90deg,#ef4444,#f59e0b)",
                }}
              />
            </div>
            <p style={{
              color: compliance?.on_track ? "#10b981" : "#ef4444",
              fontSize: 13, marginTop: 8, fontWeight: 600,
            }}>
              {compliance?.on_track
                ? `✅ On track — ${Math.abs(compliance.gap_tonnes).toFixed(0)} tonnes under target`
                : `⚠️ Off track — need ${compliance?.reduction_needed_pct?.toFixed(1)}% more reduction`}
            </p>
          </div>
        </GlassCard>

        {/* Charts Row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

          {/* Monthly Total CO2 */}
          <GlassCard title="Monthly Total CO₂ (tonnes)" delay={0.3}>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={monthlyData}>
                <defs>
                  <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.08)" />
                <XAxis dataKey="month" stroke="#334155" tick={{ fill: "#64748b", fontSize: 12 }} />
                <YAxis stroke="#334155" tick={{ fill: "#64748b", fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="total" stroke="#6366f1" strokeWidth={2}
                  fill="url(#trendGrad)" name="CO₂ (tonnes)" />
              </AreaChart>
            </ResponsiveContainer>
          </GlassCard>

          {/* MoM Change */}
          <GlassCard title="Month-over-Month Change (%)" delay={0.4}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={monthlyData.slice(1)}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.08)" />
                <XAxis dataKey="month" stroke="#334155" tick={{ fill: "#64748b", fontSize: 12 }} />
                <YAxis stroke="#334155" tick={{ fill: "#64748b", fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" />
                <Bar dataKey="mom" name="MoM Change (%)" radius={[4, 4, 0, 0]}
                  fill="#3b82f6"
                  label={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </GlassCard>
        </div>

        {/* Lane Trend */}
        <GlassCard title="Lane-Specific Trend" delay={0.5}>
          <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
            {[
              { label: "Origin", value: origin, set: setOrigin,
                options: ["Mumbai","Delhi","Chennai","Bangalore","Hyderabad","Kolkata"] },
              { label: "Destination", value: dest, set: setDest,
                options: ["Delhi","Mumbai","Bangalore","Chennai","Kolkata","Hyderabad"] },
            ].map(({ label, value, set, options }) => (
              <div key={label}>
                <label style={{ color: "#64748b", fontSize: 12, display: "block", marginBottom: 6 }}>
                  {label}
                </label>
                <select
                  value={value} onChange={e => set(e.target.value)}
                  style={{
                    background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)",
                    color: "#e2e8f0", borderRadius: 8, padding: "8px 16px", fontSize: 14,
                  }}
                >
                  {options.map(o => (
                    <option key={o} value={o} style={{ background: "#040d1f" }}>{o}</option>
                  ))}
                </select>
              </div>
            ))}
            <motion.button
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
              onClick={fetchLane}
              style={{
                marginTop: 20, background: "linear-gradient(135deg,#1e40af,#3b82f6)",
                border: "none", color: "white", borderRadius: 10,
                padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer",
              }}
            >
              Analyze Lane
            </motion.button>
            {laneTrend && (
              <div style={{ marginTop: 20, display: "flex", gap: 20 }}>
                <span style={{
                  padding: "6px 14px", borderRadius: 20, fontSize: 13, fontWeight: 600,
                  background: laneTrend.trend === "DECREASING"
                    ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
                  color: laneTrend.trend === "DECREASING" ? "#10b981" : "#ef4444",
                }}>
                  {laneTrend.trend} {Math.abs(laneTrend.trend_pct)}%
                </span>
              </div>
            )}
          </div>
          {laneData.length > 0 && (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={laneData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.08)" />
                <XAxis dataKey="period" stroke="#334155" tick={{ fill: "#64748b", fontSize: 11 }} />
                <YAxis stroke="#334155" tick={{ fill: "#64748b", fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="avg_co2" stroke="#10b981" strokeWidth={2}
                  dot={{ fill: "#10b981", r: 4 }} name="Avg CO₂ (kg)" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </GlassCard>
      </div>
    </div>
  )
}