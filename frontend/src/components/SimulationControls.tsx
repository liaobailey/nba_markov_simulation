import React, { useState, useEffect, useCallback } from 'react';
import { 
  Box, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  Button, 
  TextField,
  Paper,
  Typography,
  Grid,
  IconButton,
  Stack
} from '@mui/material';
import { KeyboardArrowUp, KeyboardArrowDown } from '@mui/icons-material';

interface SimulationControlsProps {
  teams: string[];
  seasons: string[];
  selectedTeam: string;
  selectedSeason: string;
  numSeasons: number;
  isSimulating: boolean;
  seasonsCompleted: number;
  seasonMetrics: any[];
  metricsStats: any;
  onTeamChange: (team: string) => void;
  onSeasonChange: (season: string) => void;
  onNumSeasonsChange: (numSeasons: number) => void;
  onSimulate: (additionalVars: any, adjustedMetrics: any) => void;
  onCancel: () => void;
}

const SimulationControls: React.FC<SimulationControlsProps> = ({
  teams,
  seasons,
  selectedTeam,
  selectedSeason,
  numSeasons,
  isSimulating,
  seasonsCompleted,
  seasonMetrics,
  metricsStats,
  onTeamChange,
  onSeasonChange,
  onNumSeasonsChange,
  onSimulate,
  onCancel
}) => {
  // Get metrics for selected team
  const teamMetrics = seasonMetrics.find(m => m.team_abbreviation === selectedTeam);
  
  // State for adjusted metrics
  const [adjustedMetrics, setAdjustedMetrics] = useState<any>({});
  
  // State for calculated variables
  const [calculatedVariables, setCalculatedVariables] = useState<any>({});
  
  // Reset adjusted metrics when team changes
  useEffect(() => {
    if (teamMetrics) {
      setAdjustedMetrics({
        fg2_pct: teamMetrics.fg2_pct,
        fg3_pct: teamMetrics.FG3_PCT,
        ft_pct: teamMetrics.FT_PCT,
        oreb_pct: teamMetrics.OREB_PCT,
        dreb_pct: teamMetrics.dreb_pct,
        tov_pct: teamMetrics.TM_TOV_PCT,
        opp_fg2_pct: teamMetrics.opp_fg2_pct,
        opp_fg3_pct: teamMetrics.OPP_FG3_PCT,
        opp_ft_pct: teamMetrics.OPP_FT_PCT,
        opp_oreb_pct: teamMetrics.OPP_OREB_PCT,
        opp_dreb_pct: teamMetrics.opp_dreb_pct,
        opp_tov_pct: teamMetrics.OPP_TOV_PCT,
      });
    }
  }, [teamMetrics]);
  
  const adjustMetric = (metric: string, delta: number) => {
    setAdjustedMetrics((prev: any) => ({
      ...prev,
      [metric]: Math.max(0, Math.min(1, (prev[metric] || 0) + delta))
    }));
  };
  
  const resetMetric = (metric: string, originalValue: number) => {
    setAdjustedMetrics((prev: any) => ({
      ...prev,
      [metric]: originalValue
    }));
  };

  const resetAllMetrics = () => {
    if (teamMetrics) {
      setAdjustedMetrics({
        fg2_pct: teamMetrics.fg2_pct,
        fg3_pct: teamMetrics.FG3_PCT,
        ft_pct: teamMetrics.FT_PCT,
        oreb_pct: teamMetrics.OREB_PCT,
        dreb_pct: teamMetrics.dreb_pct,
        tov_pct: teamMetrics.TM_TOV_PCT,
        opp_fg2_pct: teamMetrics.opp_fg2_pct,
        opp_fg3_pct: teamMetrics.OPP_FG3_PCT,
        opp_ft_pct: teamMetrics.OPP_FT_PCT,
        opp_oreb_pct: teamMetrics.OPP_OREB_PCT,
        opp_dreb_pct: teamMetrics.opp_dreb_pct,
        opp_tov_pct: teamMetrics.OPP_TOV_PCT,
      });
    }
  };

  // Calculate additional variables based on adjusted metrics
  const calculateVariables = useCallback(() => {
    if (!teamMetrics || !adjustedMetrics) return {};

    const original = teamMetrics;
    const adjusted = adjustedMetrics;

    // Helper function to check if metric is at default (returns 0 if so)
    const getAdditional = (adjustedValue: number, originalValue: number, formula: () => number) => {
      if (Math.abs(adjustedValue - originalValue) < 0.0001) return 0; // At default
      return formula();
    };

    return {
      // Team additional variables
      additional_shots_made_2: getAdditional(
        adjusted.fg2_pct, original.fg2_pct,
        () => (adjusted.fg2_pct * original.fg2a) - original.fg2m
      ),
      additional_shots_made_3: getAdditional(
        adjusted.fg3_pct, original.FG3_PCT,
        () => (adjusted.fg3_pct * original.FG3A) - original.FG3M
      ),
      additional_shots_made_ft: getAdditional(
        adjusted.ft_pct, original.FT_PCT,
        () => (adjusted.ft_pct * original.FTA) - original.FTM
      ),
      additional_turnovers: getAdditional(
        adjusted.tov_pct, original.TM_TOV_PCT,
        () => (adjusted.tov_pct * original.POSS) - original.TOV
      ),
      additional_dreb: getAdditional(
        adjusted.dreb_pct, original.dreb_pct,
        () => (original.DREB / original.dreb_pct) * adjusted.dreb_pct - original.DREB
      ),
      additional_oreb: getAdditional(
        adjusted.oreb_pct, original.OREB_PCT,
        () => (original.OREB / original.OREB_PCT) * adjusted.oreb_pct - original.OREB
      ),

      // Opponent additional variables
      opp_additional_shots_made_2: getAdditional(
        adjusted.opp_fg2_pct, original.opp_fg2_pct,
        () => (adjusted.opp_fg2_pct * original.opp_fg2a) - original.opp_fg2m
      ),
      opp_additional_shots_made_3: getAdditional(
        adjusted.opp_fg3_pct, original.OPP_FG3_PCT,
        () => (adjusted.opp_fg3_pct * original.OPP_FG3A) - original.OPP_FG3M
      ),
      opp_additional_shots_made_ft: getAdditional(
        adjusted.opp_ft_pct, original.OPP_FT_PCT,
        () => (adjusted.opp_ft_pct * original.OPP_FTA) - original.OPP_FTM
      ),
      opp_additional_turnovers: getAdditional(
        adjusted.opp_tov_pct, original.OPP_TOV_PCT,
        () => (adjusted.opp_tov_pct * original.POSS) - original.OPP_TOV
      ),
      opp_additional_dreb: getAdditional(
        adjusted.opp_dreb_pct, original.opp_dreb_pct,
        () => (original.OPP_DREB / original.opp_dreb_pct) * adjusted.opp_dreb_pct - original.OPP_DREB
      ),
      opp_additional_oreb: getAdditional(
        adjusted.opp_oreb_pct, original.OPP_OREB_PCT,
        () => (original.OPP_OREB / original.OPP_OREB_PCT) * adjusted.opp_oreb_pct - original.OPP_OREB
      )
    };
  }, [teamMetrics, adjustedMetrics]);

  // Recalculate variables when adjustedMetrics change
  useEffect(() => {
    if (teamMetrics && adjustedMetrics) {
      const calculated = calculateVariables();
      setCalculatedVariables(calculated);
    }
  }, [adjustedMetrics, teamMetrics, calculateVariables]);

  // Handle simulate button click
  const handleSimulateClick = () => {
    onSimulate(calculatedVariables, adjustedMetrics);
  };

  const MetricControl = ({ 
    label, 
    value, 
    metric, 
    originalValue, 
    color = '#1976d2' 
  }: { 
    label: string; 
    value: number; 
    metric: string; 
    originalValue: number; 
    color?: string; 
  }) => {
    // Map frontend metric keys to backend stats keys
    const metricKeyMapping: Record<string, string> = {
      'fg2_pct': 'fg2_pct',
      'fg3_pct': 'FG3_PCT',
      'ft_pct': 'FT_PCT',
      'oreb_pct': 'OREB_PCT',
      'dreb_pct': 'dreb_pct',
      'tov_pct': 'TM_TOV_PCT',
      'opp_fg2_pct': 'opp_fg2_pct',
      'opp_fg3_pct': 'OPP_FG3_PCT',
      'opp_ft_pct': 'OPP_FT_PCT',
      'opp_oreb_pct': 'OPP_OREB_PCT',
      'opp_dreb_pct': 'opp_dreb_pct',
      'opp_tov_pct': 'OPP_TOV_PCT'
    };
    
    // Get stats for this metric using the mapped key
    const statsKey = metricKeyMapping[metric];
    const stats = statsKey ? metricsStats[statsKey] : null;
    
    return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <TextField
          label={label}
          value={`${value ? (value * 100).toFixed(1) : 'N/A'}%`}
          InputProps={{ readOnly: true }}
          variant="outlined"
          size="small"
          sx={{ 
            flexGrow: 1,
            '& .MuiInputBase-input': { 
              color: color,
              fontWeight: 'bold',
              textAlign: 'center'
            }
          }}
        />
        <Stack direction="column" spacing={0.5}>
          <IconButton 
            size="small" 
            onClick={() => adjustMetric(metric, 0.01)}
            sx={{ color: color, p: 0.25, minWidth: 'auto' }}
          >
            <KeyboardArrowUp fontSize="small" />
          </IconButton>
          <Button
            size="small"
            variant="text"
            onClick={() => resetMetric(metric, originalValue)}
            sx={{ 
              color: '#666', 
              fontSize: '0.65rem',
              minWidth: 'auto',
              p: 0.25,
              lineHeight: 1
            }}
          >
            Reset
          </Button>
          <IconButton 
            size="small" 
            onClick={() => adjustMetric(metric, -0.01)}
            sx={{ color: color, p: 0.25, minWidth: 'auto' }}
          >
            <KeyboardArrowDown fontSize="small" />
          </IconButton>
        </Stack>
      </Box>
      {stats && (
        <Typography variant="caption" sx={{ 
          display: 'block', 
          textAlign: 'center', 
          color: '#666', 
          fontSize: '0.7rem',
          mt: 0.5
        }}>
          Min: {(stats.min * 100).toFixed(1)}% | Med: {(stats.median * 100).toFixed(1)}% | Max: {(stats.max * 100).toFixed(1)}%
        </Typography>
      )}
    </Box>
  );
  };
  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Simulation Controls
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Season</InputLabel>
          <Select
            value={selectedSeason}
            label="Season"
            onChange={(e) => onSeasonChange(e.target.value)}
            disabled={isSimulating}
          >
            {seasons.map((season) => (
              <MenuItem key={season} value={season}>
                {season}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Select Team</InputLabel>
          <Select
            value={selectedTeam}
            label="Select Team"
            onChange={(e) => onTeamChange(e.target.value)}
            disabled={isSimulating}
          >
            {teams.map((team) => (
              <MenuItem key={team} value={team}>
                {team}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <TextField
          label="Number of Seasons"
          type="number"
          value={numSeasons}
          onChange={(e) => onNumSeasonsChange(parseInt(e.target.value) || 10)}
          inputProps={{ min: 1, max: 50 }}
          sx={{ width: 150 }}
          disabled={isSimulating}
        />
        
        <Button
          variant="contained"
          onClick={handleSimulateClick}
          disabled={!selectedTeam || isSimulating}
          sx={{ 
            minWidth: 120,
            backgroundColor: '#1976d2',
            '&:hover': {
              backgroundColor: '#1565c0'
            }
          }}
        >
          {isSimulating ? `Simulating... (${seasonsCompleted}/${numSeasons})` : 'Simulate'}
        </Button>
        
        {isSimulating && (
          <Button
            variant="outlined"
            color="error"
            onClick={onCancel}
            sx={{ 
              minWidth: 120,
              borderColor: '#d32f2f',
              color: '#d32f2f',
              '&:hover': {
                borderColor: '#b71c1c',
                backgroundColor: 'rgba(211, 47, 47, 0.04)'
              }
            }}
          >
            Cancel
          </Button>
        )}
      </Box>

      {/* Metric Adjustments Section */}
      {teamMetrics && (
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Typography variant="h6">
              Metric Adjustments - {selectedTeam}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={resetAllMetrics}
              sx={{ 
                color: '#666',
                borderColor: '#666',
                '&:hover': {
                  borderColor: '#333',
                  backgroundColor: 'rgba(0,0,0,0.04)'
                }
              }}
            >
              Reset All
            </Button>
          </Box>
          
          {/* Team Metrics */}
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
            Team Metrics
          </Typography>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="2PT FG%"
                value={adjustedMetrics.fg2_pct}
                metric="fg2_pct"
                originalValue={teamMetrics?.fg2_pct || 0}
                color="#1976d2"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="3PT FG%"
                value={adjustedMetrics.fg3_pct}
                metric="fg3_pct"
                originalValue={teamMetrics?.FG3_PCT || 0}
                color="#1976d2"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="FT%"
                value={adjustedMetrics.ft_pct}
                metric="ft_pct"
                originalValue={teamMetrics?.FT_PCT || 0}
                color="#1976d2"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="OREB%"
                value={adjustedMetrics.oreb_pct}
                metric="oreb_pct"
                originalValue={teamMetrics?.OREB_PCT || 0}
                color="#1976d2"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="DREB%"
                value={adjustedMetrics.dreb_pct}
                metric="dreb_pct"
                originalValue={teamMetrics?.dreb_pct || 0}
                color="#1976d2"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="TOV%"
                value={adjustedMetrics.tov_pct}
                metric="tov_pct"
                originalValue={teamMetrics?.TM_TOV_PCT || 0}
                color="#1976d2"
              />
            </Grid>
          </Grid>

          {/* Opponent Metrics */}
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
            Opponent Metrics
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="OPP 2PT FG%"
                value={adjustedMetrics.opp_fg2_pct}
                metric="opp_fg2_pct"
                originalValue={teamMetrics?.opp_fg2_pct || 0}
                color="#9c27b0"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="OPP 3PT FG%"
                value={adjustedMetrics.opp_fg3_pct}
                metric="opp_fg3_pct"
                originalValue={teamMetrics?.OPP_FG3_PCT || 0}
                color="#9c27b0"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="OPP FT%"
                value={adjustedMetrics.opp_ft_pct}
                metric="opp_ft_pct"
                originalValue={teamMetrics?.OPP_FT_PCT || 0}
                color="#9c27b0"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="OPP OREB%"
                value={adjustedMetrics.opp_oreb_pct}
                metric="opp_oreb_pct"
                originalValue={teamMetrics?.OPP_OREB_PCT || 0}
                color="#9c27b0"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="OPP DREB%"
                value={adjustedMetrics.opp_dreb_pct}
                metric="opp_dreb_pct"
                originalValue={teamMetrics?.opp_dreb_pct || 0}
                color="#9c27b0"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <MetricControl
                label="OPP TOV%"
                value={adjustedMetrics.opp_tov_pct}
                metric="opp_tov_pct"
                originalValue={teamMetrics?.OPP_TOV_PCT || 0}
                color="#9c27b0"
              />
            </Grid>
          </Grid>

          {/* Calculated Variables */}
          <Typography variant="subtitle2" sx={{ mb: 1, mt: 3, fontWeight: 'bold' }}>
            Calculated Additional Variables
          </Typography>
          <Grid container spacing={2}>
            {/* Team additional variables */}
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Additional 2PT Made"
                value={calculatedVariables.additional_shots_made_2?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#1976d2',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Additional 3PT Made"
                value={calculatedVariables.additional_shots_made_3?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#1976d2',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Additional FT Made"
                value={calculatedVariables.additional_shots_made_ft?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#1976d2',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Additional OREB"
                value={calculatedVariables.additional_oreb?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#1976d2',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Additional DREB"
                value={calculatedVariables.additional_dreb?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#1976d2',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Additional Turnovers"
                value={calculatedVariables.additional_turnovers?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#1976d2',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
          </Grid>

          {/* Opponent additional variables */}
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="OPP Additional 2PT Made"
                value={calculatedVariables.opp_additional_shots_made_2?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#9c27b0',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="OPP Additional 3PT Made"
                value={calculatedVariables.opp_additional_shots_made_3?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#9c27b0',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="OPP Additional FT Made"
                value={calculatedVariables.opp_additional_shots_made_ft?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#9c27b0',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="OPP Additional OREB"
                value={calculatedVariables.opp_additional_oreb?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#9c27b0',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="OPP Additional DREB"
                value={calculatedVariables.opp_additional_dreb?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#9c27b0',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="OPP Additional Turnovers"
                value={calculatedVariables.opp_additional_turnovers?.toFixed(1) || '0.0'}
                InputProps={{ readOnly: true }}
                variant="outlined"
                size="small"
                sx={{ 
                  '& .MuiInputBase-input': { 
                    color: '#9c27b0',
                    fontWeight: 'bold',
                    textAlign: 'center'
                  }
                }}
              />
            </Grid>
          </Grid>
        </Box>
      )}
    </Paper>
  );
};

export default SimulationControls;

