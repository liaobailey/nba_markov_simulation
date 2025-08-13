import React from 'react';
import { Paper, Typography, Grid, Box } from '@mui/material';
import { SimulationStatistics, TEAM_WINS } from '../types';

interface SimulationStatsProps {
  stats: SimulationStatistics;
  selectedTeam: string;
  baselineWins: {[key: string]: number};
  showActualWins?: boolean;
}

const SimulationStats: React.FC<SimulationStatsProps> = ({ stats, selectedTeam, baselineWins, showActualWins = true }) => {
  const actualWins = TEAM_WINS[selectedTeam] || 0;
  const baselineWinsForTeam = baselineWins[selectedTeam] || 0;
  const difference = stats.average_expected_wins - actualWins;

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        {selectedTeam} Simulation Results
      </Typography>
      <Grid container spacing={3}>
        {/* Simulated Avg Wins */}
        <Grid item xs={12} sm={6} md={2}>
          <Box textAlign="center">
            <Typography variant="h4" color="primary" fontWeight="bold">
              {stats.average_expected_wins}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Simulated Avg Wins
            </Typography>
          </Box>
        </Grid>
        
        {/* Baseline Simulated Wins */}
        <Grid item xs={12} sm={6} md={2}>
          <Box textAlign="center">
            <Typography variant="h4" color="info.main" fontWeight="bold">
              {baselineWinsForTeam.toFixed(1)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Baseline Simulated Wins
            </Typography>
            {/* Delta from baseline */}
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
              Delta: {(stats.average_expected_wins - baselineWinsForTeam).toFixed(1)}
            </Typography>
          </Box>
        </Grid>
        
        {/* Actual Wins */}
        <Grid item xs={12} sm={6} md={2}>
          <Box textAlign="center">
            <Typography variant="h4" color="success.main" fontWeight="bold">
              {actualWins}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Actual Wins
            </Typography>
            {/* Delta from actual */}
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
              Delta: {difference.toFixed(1)}
            </Typography>
          </Box>
        </Grid>
        
        {/* Standard Deviation */}
        <Grid item xs={12} sm={6} md={2}>
          <Box textAlign="center">
            <Typography variant="h4" color="secondary" fontWeight="bold">
              {stats.standard_deviation}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Standard Deviation
            </Typography>
          </Box>
        </Grid>
        
        {/* 95% Confidence */}
        <Grid item xs={12} sm={6} md={2}>
          <Box textAlign="center">
            <Typography variant="h4" color="info.main" fontWeight="bold">
              {stats.confidence_interval_95}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              95% Confidence
            </Typography>
          </Box>
        </Grid>
        
        {/* Min - Max Wins */}
        <Grid item xs={12} sm={6} md={2}>
          <Box textAlign="center">
            <Typography variant="h4" color="warning.main" fontWeight="bold">
            {stats.min_wins} - {stats.max_wins}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Min - Max Wins
            </Typography>
          </Box>
        </Grid>
      </Grid>
      
      {/* Footnote about simulation variation */}
      <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
          Note: Simulations will vary slightly from baseline wins even with no adjustments
        </Typography>
      </Box>
    </Paper>
  );
};

export default SimulationStats;

