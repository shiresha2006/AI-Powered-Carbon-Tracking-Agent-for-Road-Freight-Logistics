import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts"
import axios from "axios"
import TopBar from "../components/Layout/TopBar"
import KPICard from "../components/shared/KPICard"
import GlassCard from "../components/shared/GlassCard"
import LoadingSpinner from "../components/shared/LoadingSpinner"
import {
  Truck, Leaf, AlertTriangle, TrendingUp,
  BarChart2, Zap, Users, Navigation
} from "lucide-react"

const COLORS = ["#3b82f6","#6366f1","#10b981","#f59e0b","#ef4444","#8b5cf6","#06b6d4","#ec4899"]

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

export default function FleetOverview() {
  const [overview,  setOverview]  = useState(null)
  const [carriers,  setCarriers]  = useState(null)
  const [polluters, setPolluters] = useState(null)
  const [monthly,   setMonthly]   = useState(null)
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    Promise.all([
      axios.get("/api/fleet/overview"),
      axios.get("/api/fleet/carriers"),
      axios.get("/api/fleet/top-polluters"),
      axios.get("/api/trends/monthly"),
    ]).then(([o, c, p, m]) => {
      setOverview(o.data)
      setCarriers(c.data)
      setPolluters(p.data)
      setMonthly(m.data)
      setLoading(false)
    })
  }, [])

  if (loading) return (
    <div style={{ marginLeft: 260, minHeight: "100vh" }}>
      <TopBar title="Fleet Overview" subtitle="Loading fleet data..." />
      <LoadingSpinner text="Fetching fleet intelligence..." />
    </div>
  )

  // Prepare chart data
  const fuelData = overview ? Object.entries(overview.fuel_mix).map(([name, value]) => ({
    name: name.toUpperCase(), value: parseFloat(value)
  })) : []

  const vehicleData = overview ? Object.entries(overview.vehicle_mix)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([name, value]) => ({
      name: name.replace(/_/g, " "), value: parseFloat(value)
    })) : []

  const monthlyData = monthly?.monthly_data?.map(m => ({
    month: `M${m.month}`,
    total_co2: Math.round(m.total_co2 / 1000),
    avg_co2:   Math.round(m.avg_co2),
    shipments: m.shipments,
  })) || []

  const carrierData = carriers?.carrier_ranking?.map(c => ({
    name:       c.carrier_name.split(" ")[0],
    avg_co2:    Math.round(c.avg_co2_kg),
    util:       Math.round(c.avg_util_pct),
    anomaly:    parseFloat((c.anomaly_rate * 100).toFixed(2)),
    performance:c.performance,
  })) || []

  const perfColor = p => p === "GREEN" ? "#10b981" : p === "AVERAGE" ? "#f59e0b" : "#ef4444"

  return (
    <div style={{ marginLeft: 260, minHeight: "100vh" }}>
      <TopBar
        title="Fleet Overview"
        subtitle={`2024 · ${overview?.total_shipments?.toLocaleString()} shipments · ${overview?.unique_carriers} carriers`}
      />
      <div style={{ padding: "28px 28px 40px" }}>

        {/* KPI Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 }}>
          <KPICard
            title="Total CO₂ Emissions"
            value={overview?.total_co2_tonnes?.toLocaleString()}
            unit="tonnes"
            subtitle="Tank-to-Wheel 2024"
            icon={Leaf} color="green" delay={0}
          />
          <KPICard
            title="Total Shipments"
            value={overview?.total_shipments?.toLocaleString()}
            unit=""
            subtitle={`${overview?.unique_lanes} active lanes`}
            icon={Truck} color="blue" delay={0.1}
          />
          <KPICard
            title="Carbon Intensity"
            value={overview?.carbon_intensity_g_tkm?.toFixed(1)}
            unit="g/tkm"
            subtitle="vs 130 g/tkm industry avg"
            icon={TrendingUp} color="indigo" delay={0.2}
          />
          <KPICard
            title="Anomaly Rate"
            value={overview?.anomaly_rate_pct?.toFixed(2)}
            unit="%"
            subtitle="Of total shipments"
            icon={AlertTriangle} color="red" delay={0.3}
          />
          <KPICard
            title="Avg CO₂ / Shipment"
            value={Math.round(overview?.avg_co2_per_shipment)?.toLocaleString()}
            unit="kg"
            subtitle="Per delivery"
            icon={BarChart2} color="amber" delay={0.4}
          />
          <KPICard
            title="Load Utilization"
            value={overview?.avg_load_util_pct?.toFixed(1)}
            unit="%"
            subtitle="Fleet average"
            icon={Zap} color="cyan" delay={0.5}
          />
          <KPICard
            title="Empty Return Rate"
            value={overview?.empty_return_pct?.toFixed(1)}
            unit="%"
            subtitle="Revenue loss opportunity"
            icon={Navigation} color="red" delay={0.6}
          />
          <KPICard
            title="Active Carriers"
            value={overview?.unique_carriers}
            unit=""
            subtitle="Across all lanes"
            icon={Users} color="indigo" delay={0.7}
          />
        </div>

        {/* Row 2 — Charts */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginBottom: 16 }}>

          {/* Monthly CO2 Area Chart */}
          <GlassCard title="Monthly CO₂ Emissions (tonnes)" delay={0.3}>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={monthlyData}>
                <defs>
                  <linearGradient id="co2Grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.08)" />
                <XAxis dataKey="month" stroke="#334155" tick={{ fill: "#64748b", fontSize: 12 }} />
                <YAxis stroke="#334155" tick={{ fill: "#64748b", fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone" dataKey="total_co2"
                  stroke="#3b82f6" strokeWidth={2}
                  fill="url(#co2Grad)" name="CO₂ (tonnes)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </GlassCard>

          {/* Fuel Mix Pie */}
          <GlassCard title="Fuel Mix" delay={0.4}>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={fuelData} cx="50%" cy="50%"
                  innerRadius={55} outerRadius={90}
                  paddingAngle={4} dataKey="value"
                >
                  {fuelData.map((_, i) => (
                    <Cell
                      key={i} fill={COLORS[i]}
                      stroke="rgba(2,8,24,0.5)" strokeWidth={2}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  formatter={v => (
                    <span style={{ color: "#94a3b8", fontSize: 12 }}>{v}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </GlassCard>
        </div>

        {/* Row 3 */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

          {/* Carrier Performance */}
          <GlassCard title="Carrier Avg CO₂ (kg/shipment)" delay={0.5}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={carrierData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.08)" horizontal={false} />
                <XAxis type="number" stroke="#334155" tick={{ fill: "#64748b", fontSize: 11 }} />
                <YAxis type="category" dataKey="name" stroke="#334155" tick={{ fill: "#64748b", fontSize: 11 }} width={80} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="avg_co2" name="Avg CO₂ (kg)" radius={[0, 4, 4, 0]}>
                  {carrierData.map((c, i) => (
                    <Cell key={i} fill={perfColor(c.performance)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </GlassCard>

          {/* Vehicle Mix */}
          <GlassCard title="Vehicle Type Mix (%)" delay={0.6}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={vehicleData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.08)" />
                <XAxis dataKey="name" stroke="#334155" tick={{ fill: "#64748b", fontSize: 10 }} angle={-20} textAnchor="end" height={50} />
                <YAxis stroke="#334155" tick={{ fill: "#64748b", fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="value" name="Share (%)" radius={[4, 4, 0, 0]}>
                  {vehicleData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </GlassCard>
        </div>

        {/* Top Polluters Table */}
        <GlassCard title="Top 10 Highest Emission Shipments" delay={0.7}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Shipment ID","Route","Vehicle","Carrier","CO₂ (kg)","Load %","Anomaly"].map(h => (
                    <th key={h} style={{
                      textAlign: "left", padding: "10px 14px",
                      color: "#64748b", fontSize: 12, fontWeight: 600,
                      borderBottom: "1px solid rgba(59,130,246,0.1)",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {polluters?.shipments?.map((s, i) => (
                  <motion.tr
                    key={s.shipment_id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.8 + i * 0.05 }}
                    whileHover={{ background: "rgba(59,130,246,0.06)" }}
                    style={{ borderBottom: "1px solid rgba(59,130,246,0.06)" }}
                  >
                    <td style={{ padding: "10px 14px", color: "#3b82f6", fontSize: 13, fontWeight: 600 }}>
                      {s.shipment_id}
                    </td>
                    <td style={{ padding: "10px 14px", color: "#e2e8f0", fontSize: 13 }}>
                      {s.origin} → {s.destination}
                    </td>
                    <td style={{ padding: "10px 14px", color: "#94a3b8", fontSize: 12 }}>
                      {s.vehicle_type?.replace(/_/g, " ")}
                    </td>
                    <td style={{ padding: "10px 14px", color: "#94a3b8", fontSize: 12 }}>
                      {s.carrier_name}
                    </td>
                    <td style={{ padding: "10px 14px", color: "#f59e0b", fontSize: 13, fontWeight: 600 }}>
                      {s.co2_kg?.toLocaleString()}
                    </td>
                    <td style={{ padding: "10px 14px", color: "#94a3b8", fontSize: 13 }}>
                      {s.load_utilization_pct?.toFixed(1)}%
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <span style={{
                        padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 600,
                        background: s.is_anomaly ? "rgba(239,68,68,0.15)" : "rgba(16,185,129,0.15)",
                        color: s.is_anomaly ? "#ef4444" : "#10b981",
                      }}>
                        {s.is_anomaly ? "ANOMALY" : "Normal"}
                      </span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}