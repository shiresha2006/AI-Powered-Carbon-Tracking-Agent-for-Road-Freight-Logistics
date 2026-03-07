import { BrowserRouter, Routes, Route } from "react-router-dom"
import { AnimatePresence } from "framer-motion"
import ParticleBackground from "./components/particles/ParticleBackground"
import Sidebar from "./components/Layout/Sidebar"
import FleetOverview   from "./pages/FleetOverview"
import AnomalyMonitor  from "./pages/AnomalyMonitor"
import TrendAnalysis   from "./pages/TrendAnalysis"
import ReductionAdvisor from "./pages/ReductionAdvisor"
import ESGReport       from "./pages/ESGReport"
import AskLORRI        from "./pages/AskLORRI"

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: "100vh", background: "#020818", position: "relative" }}>
        <ParticleBackground />
        <div style={{ position: "relative", zIndex: 1 }}>
          <Sidebar />
          <main>
            <AnimatePresence mode="wait">
              <Routes>
                <Route path="/"          element={<FleetOverview />}    />
                <Route path="/anomaly"   element={<AnomalyMonitor />}   />
                <Route path="/trends"    element={<TrendAnalysis />}     />
                <Route path="/reduction" element={<ReductionAdvisor />}  />
                <Route path="/esg"       element={<ESGReport />}         />
                <Route path="/chat"      element={<AskLORRI />}          />
              </Routes>
            </AnimatePresence>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}