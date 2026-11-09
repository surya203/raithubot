import { BrowserRouter, Route, Routes } from "react-router-dom"
import { FarmProvider } from "./context/FarmContext"
import AppLayout from "./layouts/AppLayout"
import Dashboard from "./pages/Dashboard"
import Crops from "./pages/Crops"
import Disease from "./pages/Disease"
import Assistant from "./pages/Assistant"
import Alerts from "./pages/Alerts"
import History from "./pages/History"
import Knowledge from "./pages/Knowledge"

export default function App() {
  return (
    <BrowserRouter>
      <FarmProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="crops" element={<Crops />} />
            <Route path="disease" element={<Disease />} />
            <Route path="assistant" element={<Assistant />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="history" element={<History />} />
            <Route path="knowledge" element={<Knowledge />} />
          </Route>
        </Routes>
      </FarmProvider>
    </BrowserRouter>
  )
}
