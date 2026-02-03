import React, { useState, useEffect } from 'react'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
} from '@mui/material'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { getDashboardOverview, getExecutionTrends } from '../services/api'

function StatCard({ title, value, subtitle, color = 'primary' }) {
  return (
    <Card>
      <CardContent>
        <Typography color="textSecondary" gutterBottom>
          {title}
        </Typography>
        <Typography variant="h4" component="div" color={color}>
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="textSecondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  )
}

function Dashboard() {
  const [overview, setOverview] = useState(null)
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [overviewRes, trendsRes] = await Promise.all([
        getDashboardOverview(),
        getExecutionTrends(7, 'day'),
      ])

      setOverview(overviewRes.data)
      setTrends(trendsRes.data)
    } catch (error) {
      console.error('Error loading dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  // Transform trends data for chart
  const chartData = trends?.periods.map((period, i) => ({
    date: period,
    executions: trends.total_executions[i],
    successful: trends.successful_executions[i],
  })) || []

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Business Overview
      </Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total SOPs"
            value={overview?.total_sops || 0}
            subtitle="Active procedures"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Executions (30d)"
            value={overview?.total_executions_30d || 0}
            subtitle="Total executions"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Success Rate"
            value={`${Math.round((overview?.success_rate || 0) * 100)}%`}
            subtitle="Overall success"
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Automation"
            value={`${Math.round((overview?.avg_automation_level || 0) * 100)}%`}
            subtitle="Average automation"
            color="secondary"
          />
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Execution Trends (Last 7 Days)
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="executions"
                stroke="#8884d8"
                name="Total Executions"
              />
              <Line
                type="monotone"
                dataKey="successful"
                stroke="#82ca9d"
                name="Successful"
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Box sx={{ mt: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Active Processes (24h)
                </Typography>
                <Typography variant="h3" color="primary">
                  {overview?.active_processes_24h || 0}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Processes executed in last 24 hours
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quick Actions
                </Typography>
                <Typography variant="body2">
                  • Create new SOP
                </Typography>
                <Typography variant="body2">
                  • Execute workflow
                </Typography>
                <Typography variant="body2">
                  • View analytics
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Box>
  )
}

export default Dashboard
