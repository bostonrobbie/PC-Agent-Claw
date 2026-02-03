import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material'
import { Add as AddIcon } from '@mui/icons-material'
import { listSOPs } from '../services/api'

function SOPs() {
  const navigate = useNavigate()
  const [sops, setSOPs] = useState([])

  useEffect(() => {
    loadSOPs()
  }, [])

  const loadSOPs = async () => {
    try {
      const response = await listSOPs()
      setSOPs(response.data.sops || [])
    } catch (error) {
      console.error('Error loading SOPs:', error)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      active: 'success',
      draft: 'warning',
      archived: 'default',
    }
    return colors[status] || 'default'
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Standard Operating Procedures</Typography>
        <Button variant="contained" startIcon={<AddIcon />}>
          Create SOP
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>SOP Code</TableCell>
              <TableCell>Title</TableCell>
              <TableCell>Function</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Automation</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sops.map((sop) => (
              <TableRow
                key={sop.id}
                hover
                onClick={() => navigate(`/sops/${sop.id}`)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>{sop.sop_code}</TableCell>
                <TableCell>{sop.sop_title}</TableCell>
                <TableCell>{sop.function_name || '-'}</TableCell>
                <TableCell>
                  <Chip label={sop.status} color={getStatusColor(sop.status)} size="small" />
                </TableCell>
                <TableCell>{Math.round((sop.automation_level || 0) * 100)}%</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default SOPs
