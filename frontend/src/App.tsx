import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import ConnectPage from './pages/ConnectPage'
import DashboardPage from './pages/DashboardPage'
import ERDiagramPage from './pages/ERDiagramPage'
import DictionaryPage from './pages/DictionaryPage'
import QualityPage from './pages/QualityPage'
import QueryPage from './pages/QueryPage'
import { useAppStore } from './store/useAppStore'

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { connectionId } = useAppStore()
  if (!connectionId) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ConnectPage />} />
        <Route path="/dashboard" element={<ProtectedRoute><Layout><DashboardPage /></Layout></ProtectedRoute>} />
        <Route path="/er-diagram" element={<ProtectedRoute><Layout><ERDiagramPage /></Layout></ProtectedRoute>} />
        <Route path="/dictionary" element={<ProtectedRoute><Layout><DictionaryPage /></Layout></ProtectedRoute>} />
        <Route path="/quality" element={<ProtectedRoute><Layout><QualityPage /></Layout></ProtectedRoute>} />
        <Route path="/query" element={<ProtectedRoute><Layout><QueryPage /></Layout></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}