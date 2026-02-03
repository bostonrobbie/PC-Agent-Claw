import React, { useState, useEffect } from 'react'
import { Box, Typography, Card, CardContent, Grid } from '@mui/material'
import { getAutomationStatus } from '../services/api'

function Automation() {
  const [status, setStatus] = useState(null)

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      const response = await getAutomationStatus()
      setStatus(response.data)
    } catch (error) {
      console.error('Error loading automation status:', error)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Process Automation
      </Typography>

      {status && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Total Steps</Typography>
                <Typography variant="h3">{status.total_steps || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Automated Steps</Typography>
                <Typography variant="h3">{status.automated_steps || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Automation Rate</Typography>
                <Typography variant="h3">
                  {Math.round((status.automation_rate || 0) * 100)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  )
}

export default Automation
