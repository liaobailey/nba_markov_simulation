import React, { useState, useEffect } from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Container, 
  Box, 
  Alert,
  CircularProgress,
  ThemeProvider,
  createTheme
} from '@mui/material';
import '@fontsource/archivo';
import SimulationControls from './components/SimulationControls';
import SimulationChart from './components/SimulationChart';
import SimulationStats from './components/SimulationStats';
import { getTeams, simulateSeasonsStream, healthCheck, getSeasonMetrics, getSeasons, getBaselineWins, cancelSimulation } from './api/api';
import { SimulationResult } from './types';

const theme = createTheme({
  typography: {
    h4: {
      fontFamily: 'Archivo, sans-serif',
      fontWeight: 800,
      letterSpacing: '-0.5px',
    },
  },
});

function App() {
  const [teams, setTeams] = useState<string[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string>('');
  const [selectedSeason, setSelectedSeason] = useState<string>('2024-25');
  const [seasons, setSeasons] = useState<string[]>([]);
  const [numSeasons, setNumSeasons] = useState<number>(10);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [seasonsCompleted, setSeasonsCompleted] = useState<number>(0);
  const [lastSimulatedTeam, setLastSimulatedTeam] = useState<string>('');
  const [seasonMetrics, setSeasonMetrics] = useState<any[]>([]);
  const [metricsStats, setMetricsStats] = useState<any>({});
  const [baselineWins, setBaselineWins] = useState<{[key: string]: number}>({});

  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Check backend health
        const isHealthy = await healthCheck();
        if (!isHealthy) {
          setError('Backend server is not available. Please ensure the backend is running.');
          setIsLoading(false);
          return;
        }

        // Load teams
        const teamsList = await getTeams();
        setTeams(teamsList);
        if (teamsList.length > 0) {
          setSelectedTeam(teamsList[0]);
        }

        // Load available seasons
        const seasonsList = await getSeasons();
        setSeasons(seasonsList);
        if (seasonsList.length > 0) {
          setSelectedSeason(seasonsList[0]);
        }

        // Load season metrics
        const data = await getSeasonMetrics(selectedSeason);
        setSeasonMetrics(data.metrics);
        setMetricsStats(data.stats);
        
        // Load baseline wins
        const baselineData = await getBaselineWins(selectedSeason);
        setBaselineWins(baselineData);

        setIsLoading(false);
      } catch (err: any) {
        let errorMessage = 'Failed to load teams. Please check your connection.';
        
        if (err.message) {
          errorMessage = err.message;
        } else if (typeof err === 'string') {
          errorMessage = err;
        } else if (err && typeof err === 'object') {
          errorMessage = JSON.stringify(err);
        }
        
        setError(errorMessage);
        setIsLoading(false);
      }
    };

    initializeApp();
  }, [selectedSeason]);

  useEffect(() => {
    const loadSeasonMetrics = async () => {
      try {
        const data = await getSeasonMetrics(selectedSeason);
        setSeasonMetrics(data.metrics);
        setMetricsStats(data.stats);
      } catch (err: any) {
        let errorMessage = 'Failed to load season metrics. Please check your connection.';
        
        if (err.response?.data?.detail) {
          errorMessage = err.response.data.detail;
        } else if (err.message) {
          errorMessage = err.message;
        } else if (typeof err === 'string') {
          errorMessage = err;
        } else if (err && typeof err === 'object') {
          errorMessage = JSON.stringify(err);
        }
        
        setError(errorMessage);
      }
    };

    loadSeasonMetrics();
  }, [selectedSeason]);

  const handleSimulate = async (additionalVars: any, adjustedMetrics: any) => {
    if (!selectedTeam) return;

    setIsSimulating(true);
    setError('');
    setSimulationResult(null);
    setSeasonsCompleted(0);
    setLastSimulatedTeam(selectedTeam);

    try {
      const seasons: any[] = [];

      await simulateSeasonsStream(
        selectedTeam,
        numSeasons,
        selectedSeason,
        additionalVars,  // Pass the calculated additional variables
        adjustedMetrics,  // Pass the adjusted metrics
        // onSeasonUpdate
        (seasonData: any) => {
          seasons.push(seasonData);
          setSeasonsCompleted(seasons.length);
          
          // Update the result with current seasons
          setSimulationResult({
            seasons: [...seasons],
            statistics: seasonData.running_statistics || {
              average_expected_wins: 0,
              standard_deviation: 0,
              confidence_interval_95: 0,
              min_wins: 0,
              max_wins: 0,
              seasons_completed: 0
            }
          });
        },
        // onStatsUpdate
        (stats: any) => {
          setSimulationResult(prev => prev ? {
            ...prev,
            statistics: stats
          } : null);
        },
        // onComplete
        () => {
          setIsSimulating(false);
        },
        // onError
        (err: any) => {
          console.log('Error object:', err); // Debug log
          console.log('Error type:', typeof err); // Debug log
          
          // Handle different types of error objects
          let errorMessage = 'Simulation failed. Please try again.';
          
          if (err.message) {
            errorMessage = err.message;
          } else if (typeof err === 'string') {
            errorMessage = err;
          } else if (err && typeof err === 'object') {
            // Convert error object to string
            errorMessage = JSON.stringify(err);
          }
          
          setError(errorMessage);
          setIsSimulating(false);
        }
      );
    } catch (err: any) {
      console.log('Error object:', err); // Debug log
      console.log('Error type:', typeof err); // Debug log
      
      // Handle different types of error objects
      let errorMessage = 'Simulation failed. Please try again.';
      
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.response?.data) {
        // Handle validation errors or other structured error responses
        if (typeof err.response.data === 'object') {
          errorMessage = JSON.stringify(err.response.data);
        } else {
          errorMessage = String(err.response.data);
        }
      } else if (err.message) {
        errorMessage = err.message;
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else if (err && typeof err === 'object') {
        // Convert error object to string
        errorMessage = JSON.stringify(err);
      }
      
      setError(errorMessage);
      setIsSimulating(false);
    }
  };

  const handleCancel = async () => {
    try {
      await cancelSimulation(selectedTeam);
      setIsSimulating(false);
      // Don't show error message for user-initiated cancellation
    } catch (err) {
      console.error('Cancellation error:', err);
      setError('Failed to cancel simulation');
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ flexGrow: 1 }}>
        <AppBar 
          position="static" 
          sx={{ 
            backgroundColor: '#1e3a8a', // Deep blue color
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}
        >
          <Toolbar>
            <Typography 
              variant="h4" 
              component="h1" 
              sx={{ 
                flexGrow: 1,
                fontWeight: 800,
                letterSpacing: '-0.5px',
                color: 'white'
              }}
            >
              NBA Markov Simulation
            </Typography>
          </Toolbar>
        </AppBar>

        <Container maxWidth="xl" sx={{ py: 4 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <SimulationControls
            teams={teams}
            seasons={seasons}
            selectedTeam={selectedTeam}
            selectedSeason={selectedSeason}
            numSeasons={numSeasons}
            isSimulating={isSimulating}
            seasonsCompleted={seasonsCompleted}
            seasonMetrics={seasonMetrics}
            metricsStats={metricsStats}
            onTeamChange={setSelectedTeam}
            onSeasonChange={setSelectedSeason}
            onNumSeasonsChange={setNumSeasons}
            onSimulate={handleSimulate}
            onCancel={handleCancel}
          />

          {simulationResult && (
            <>
              <SimulationStats 
                stats={simulationResult.statistics} 
                selectedTeam={lastSimulatedTeam}
                baselineWins={baselineWins}
              />
              <SimulationChart 
                seasons={simulationResult.seasons} 
                selectedTeam={selectedTeam} 
              />
            </>
          )}
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;

