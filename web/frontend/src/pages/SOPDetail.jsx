import React from 'react'
import { useParams } from 'react-router-dom'
import { Box, Typography } from '@mui/material'

function SOPDetail() {
  const { id } = useParams()
  return (
    <Box>
      <Typography variant="h4">SOP Detail: {id}</Typography>
      <Typography>SOP detail view coming soon...</Typography>
    </Box>
  )
}

export default SOPDetail
