import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Box } from '@mui/material'
import Navigation from './components/Navigation'
import Dashboard from './pages/Dashboard'
import SOPs from './pages/SOPs'
import SOPDetail from './pages/SOPDetail'
import Workflows from './pages/Workflows'
import WorkflowDetail from './pages/WorkflowDetail'
import Analytics from './pages/Analytics'
import Automation from './pages/Automation'

function App() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Navigation />
      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sops" element={<SOPs />} />
          <Route path="/sops/:id" element={<SOPDetail />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/workflows/:id" element={<WorkflowDetail />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/automation" element={<Automation />} />
        </Routes>
      </Box>
    </Box>
  )
}

export default App
