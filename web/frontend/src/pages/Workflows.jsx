import React, { useState, useEffect } from 'react'
import { Box, Typography, Button, Grid, Card, CardContent } from '@mui/material'
import { Add as AddIcon } from '@mui/icons-material'
import { listWorkflows } from '../services/api'

function Workflows() {
  const [workflows, setWorkflows] = useState([])

  useEffect(() => {
    loadWorkflows()
  }, [])

  const loadWorkflows = async () => {
    try {
      const response = await listWorkflows()
      setWorkflows(response.data.workflows || [])
    } catch (error) {
      console.error('Error loading workflows:', error)
    }
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Workflows</Typography>
        <Button variant="contained" startIcon={<AddIcon />}>
          Create Workflow
        </Button>
      </Box>

      <Grid container spacing={3}>
        {workflows.map((workflow) => (
          <Grid item xs={12} md={6} lg={4} key={workflow.id}>
            <Card>
              <CardContent>
                <Typography variant="h6">{workflow.workflow_name}</Typography>
                <Typography variant="body2" color="textSecondary">
                  {workflow.description || 'No description'}
                </Typography>
                <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                  Type: {workflow.workflow_type}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

export default Workflows
