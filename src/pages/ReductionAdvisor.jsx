import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from "recharts"
import axios from "axios"
import TopBar from "../components/Layout/TopBar"
import GlassCard from "../components/shared/GlassCard"
import KPICard from "../components/shared/KPICard"
import LoadingSpinner from "../components/shared/LoadingSpinner"
import { Lightbulb, Zap, TrendingDown, BarChart2 } from "lucide-react"

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

export default function ReductionAdvisor() {
  const [opps,      setOpps]      = useState(null)
  const [topLanes,  setTopLanes]  = useState(null)
  const [simulation,setSimulation]= useState(null)
  const [loading,   setLoading]   = useState(true)
  const [simLoading,setSimLoading]= useState(false)
  const [origin,    setOrigin]    = useState("Mumbai")
  const [dest,      setDest]      = useState("Delhi")
  const [fromFuel,  setFromFuel]  = useState("diesel")
  const [toFuel,    setToFuel]    = useState("cng")

  useEffect(() => {
    Promise.all([
      axios.get("/api/reduction/opportunities?top_n=10"),
      axios.get("/api/reduction/top-lanes?top_n=10"),
    ]).then(([o, l]) => {
      setOpps(o.data)
      setTopLanes(l.data)
      setLoading(false)
    })
  }, [])

  const simulate = () => {
    setSimLoading(true)
    axios.get(`/api/reduction/fuel-switch?origin=${origin}&destination=${dest}&from_fuel=${fromFuel}&to_fuel=${toFuel}`)
      .then(r => { setSimulation(r.data); setSimLoading(false) })
  }

  if (loading) return (
    <div style={{ marginLeft: 260 }}>
      <TopBar title="Reduction Advisor" />
      <LoadingSpinner text="Calculating reduction opportunities..." />
    </div>
  )

  const typeColor = t => t === "FUEL_SWITCH" ? "#3b82f6" : t === "BACKHAUL_OPTIMIZATION" ? "#10b981" : "#f59e0b"
  const priorityColor = p => p === "HIGH" ? "#ef4444" : p === "MEDIUM" ? "#f59e0b" : "#10b981"

  const topLanesData = topLanes?.top_lanes?.slice(0, 8).map(l => ({
    lane:  `${l.origin?.slice(0,3)}→${l.destination?.slice(0,3)}`,
    total: Math.round(l.total_co2_kg / 1000),
    avg:   Math.round(l.avg_co2_kg),
  })) || []

  return (
    <div style={{ marginLeft: 260, minHeight: "100vh" }}>
      <TopBar title="Reduction Advisor" subtitle="Identify and simulate CO₂ reduction opportunities" />
      <div style={{ padding: "28px 28px 40px" }}>

        {/* KPIs */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 }}>
          <KPICard
            title="Total Potential Saving"
            value={Math.round((opps?.total_potential_saving_kg || 0) / 1000).toLocaleString()}
            unit="tonnes CO₂"
            subtitle="Across all opportunities"
            icon={TrendingDown} color="green" delay={0}
          />
          <KPICard
            title="Max Reduction"
            value={opps?.max_reduction_pct?.toFixed(1)}
            unit="%"
            subtitle="Of fleet total CO₂"
            icon={BarChart2} color="indigo" delay={0.1}
          />
          <KPICard
            title="Fleet Total CO₂"
            value={Math.round((opps?.fleet_total_co2_kg || 0) / 1000).toLocaleString()}
            unit="tonnes"
            subtitle="Current baseline"
            icon={Zap} color="amber" delay={0.2}
          />
          <KPICard
            title="Opportunities Found"
            value={opps?.top_opportunities?.length || 0}
            unit=""
            subtitle="Actionable reductions"
            icon={Lightbulb} color="blue" delay={0.3}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

          {/* Opportunity Cards */}
          <GlassCard title="Top Reduction Opportunities" delay={0.2}>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 480, overflowY: "auto" }}>
              {opps?.top_opportunities?.map((o, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.07 }}
                  whileHover={{ x: 4, boxShadow: `0 8px 24px ${typeColor(o.type)}20` }}
                  style={{
                    padding: "14px 16px", borderRadius: 12,
                    background: `${typeColor(o.type)}10`,
                    border: `1px solid ${typeColor(o.type)}25`,
                    cursor: "default",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: "2px 8px",
                        borderRadius: 20, background: `${typeColor(o.type)}20`,
                        color: typeColor(o.type),
                      }}>
                        {o.type?.replace(/_/g, " ")}
                      </span>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: "2px 8px",
                        borderRadius: 20, background: `${priorityColor(o.priority)}15`,
                        color: priorityColor(o.priority),
                      }}>
                        {o.priority}
                      </span>
                    </div>
                    <span style={{ color: "#10b981", fontSize: 14, fontWeight: 700 }}>
                      -{Math.round(o.saving_kg / 1000).toLocaleString()}t
                    </span>
                  </div>
                  <p style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                    {o.lane}
                  </p>
                  <p style={{ color: "#64748b", fontSize: 12 }}>{o.action}</p>
                  <div style={{ marginTop: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ color: "#64748b", fontSize: 11 }}>
                        {o.shipments} shipments affected
                      </span>
                    </div>
                    <div style={{ background: "rgba(255,255,255,0.05)", borderRadius: 4, height: 4 }}>
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min((o.saving_kg / (opps?.top_opportunities?.[0]?.saving_kg || 1)) * 100, 100)}%` }}
                        transition={{ delay: 0.5 + i * 0.1, duration: 0.8 }}
                        style={{ height: "100%", borderRadius: 4, background: typeColor(o.type) }}
                      />
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>

          {/* Top Emission Lanes Bar Chart */}
          <GlassCard title="Top Emission Lanes (tonnes CO₂)" delay={0.3}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topLanesData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.08)" horizontal={false} />
                <XAxis type="number" stroke="#334155" tick={{ fill: "#64748b", fontSize: 11 }} />
                <YAxis type="category" dataKey="lane" width={70} stroke="#334155" tick={{ fill: "#64748b", fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="total" name="Total CO₂ (t)" radius={[0, 4, 4, 0]}>
                  {topLanesData.map((_, i) => (
                    <Cell key={i} fill={i < 3 ? "#ef4444" : i < 6 ? "#f59e0b" : "#3b82f6"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </GlassCard>
        </div>

        {/* Fuel Switch Simulator */}
        <GlassCard title="⚡ Fuel Switch Simulator" delay={0.5}>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 20 }}>
            {[
              { label: "Origin", value: origin, set: setOrigin,
                options: ["Mumbai","Delhi","Chennai","Bangalore","Hyderabad","Kolkata","Nagpur","Pune"] },
              { label: "Destination", value: dest, set: setDest,
                options: ["Delhi","Mumbai","Bangalore","Chennai","Kolkata","Hyderabad","Nagpur","Pune"] },
              { label: "From Fuel", value: fromFuel, set: setFromFuel,
                options: ["diesel","cng"] },
              { label: "To Fuel", value: toFuel, set: setToFuel,
                options: ["cng","electric","diesel"] },
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
              onClick={simulate}
              style={{
                marginTop: 20, background: "linear-gradient(135deg,#065f46,#10b981)",
                border: "none", color: "white", borderRadius: 10,
                padding: "10px 28px", fontSize: 14, fontWeight: 600, cursor: "pointer",
                boxShadow: "0 4px 20px rgba(16,185,129,0.3)",
              }}
            >
              {simLoading ? "Simulating..." : "Simulate Saving"}
            </motion.button>
          </div>

          {simulation && !simLoading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 }}
            >
              {[
                { label: "Current Avg CO₂",   value: `${simulation.current_avg_co2_kg?.toLocaleString()} kg`,    color: "#ef4444" },
                { label: "Projected Avg CO₂", value: `${simulation.projected_avg_co2_kg?.toLocaleString()} kg`,   color: "#10b981" },
                { label: "Saving / Shipment",  value: `${simulation.saving_per_shipment_kg?.toLocaleString()} kg`, color: "#3b82f6" },
                { label: "Annual Total Saving",value: `${Math.round(simulation.total_annual_saving_kg/1000).toLocaleString()}t CO₂`, color: "#f59e0b" },
              ].map(({ label, value, color }) => (
                <div key={label} style={{
                  background: `${color}10`, border: `1px solid ${color}25`,
                  borderRadius: 12, padding: "16px 20px", textAlign: "center",
                }}>
                  <div style={{ color, fontSize: 20, fontWeight: 700 }}>{value}</div>
                  <div style={{ color: "#64748b", fontSize: 12, marginTop: 4 }}>{label}</div>
                </div>
              ))}
            </motion.div>
          )}
        </GlassCard>
      </div>
    </div>
  )
}