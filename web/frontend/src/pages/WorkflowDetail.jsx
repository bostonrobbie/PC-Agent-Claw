import React from 'react'
import { useParams } from 'react-router-dom'
import { Box, Typography } from '@mui/material'

function WorkflowDetail() {
  const { id } = useParams()
  return (
    <Box>
      <Typography variant="h4">Workflow Detail: {id}</Typography>
      <Typography>Workflow visual designer coming soon...</Typography>
    </Box>
  )
}

export default WorkflowDetail
