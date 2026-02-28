import { Navigate, Route, Routes } from "react-router-dom"

import { NavHeader } from "@/components/NavHeader"
import { AreaDetailsPage } from "@/pages/AreaDetailsPage"
import { ComparePage } from "@/pages/ComparePage"
import { DashboardPage } from "@/pages/DashboardPage"
import { NotFoundPage } from "@/pages/NotFoundPage"

export function App() {
  return (
    <>
      <NavHeader />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/areas/:areaId" element={<AreaDetailsPage />} />
        <Route path="/home" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </>
  )
}

export default App
