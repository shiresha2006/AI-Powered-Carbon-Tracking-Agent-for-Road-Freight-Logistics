export default function LoadingSpinner({ text = "Loading..." }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      padding: "60px 20px", gap: 16,
    }}>
      <div style={{
        width: 48, height: 48, border: "3px solid rgba(59,130,246,0.2)",
        borderTop: "3px solid #3b82f6", borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <p style={{ color: "#64748b", fontSize: "14px" }}>{text}</p>
    </div>
  )
}