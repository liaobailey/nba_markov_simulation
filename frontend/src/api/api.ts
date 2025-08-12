import axios from 'axios';
import { SimulationResult } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getTeams = async (): Promise<string[]> => {
  const response = await api.get<{ teams: string[] }>('/teams');
  return response.data.teams;
};

export const getSeasons = async (): Promise<string[]> => {
  const response = await api.get<{ seasons: string[] }>('/api/seasons');
  return response.data.seasons;
};

export const getBaselineWins = async (season: string = '2024-25'): Promise<{[key: string]: number}> => {
  const response = await api.get<{ baseline_wins: {[key: string]: number} }>(`/api/baseline-wins?season=${season}`);
  return response.data.baseline_wins;
};

export const simulateSeasons = async (
  team: string, 
  numSeasons: number = 10
): Promise<SimulationResult> => {
  const response = await api.post<SimulationResult>('/api/simulate', {
    team,
    num_seasons: numSeasons
  });
  return response.data;
};

export const simulateSeasonsStream = async (
  team: string,
  numSeasons: number = 10,
  season: string = '2024-25',
  additionalVars: any = {},
  adjustedMetrics: any = {},
  onSeasonUpdate: (seasonData: any) => void,
  onStatsUpdate: (stats: any) => void,
  onComplete: () => void,
  onError: (error: any) => void
): Promise<void> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/simulate/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        team,
        num_seasons: numSeasons,
        season,
        additional_vars: additionalVars,
        adjusted_metrics: adjustedMetrics
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            // Check if it's final statistics
            if (data.type === 'final_statistics') {
              onStatsUpdate(data.statistics);
              onComplete();
            } else if (data.type === 'cancelled') {
              onComplete(); // Call onComplete to clean up UI
              console.log('Simulation cancelled:', data.message);
            } else if (data.season && data.games) {
              // This is season data
              onSeasonUpdate(data);
            }
          } catch (e) {
            console.error('Error parsing stream data:', e);
          }
        }
      }
    }
  } catch (error) {
    onError(error);
  }
};

export const getSeasonMetrics = async (season: string = '2024-25'): Promise<{metrics: any[], stats: any}> => {
  const response = await api.get(`/api/season-metrics?season=${season}`);
  return response.data;
};

export const cancelSimulation = async (team: string): Promise<void> => {
  await api.post('/api/simulate/cancel', { team });
};

export const healthCheck = async (): Promise<boolean> => {
  try {
    const response = await api.get('/health');
    return response.data.status === 'healthy';
  } catch (error) {
    return false;
  }
};

export const generateTransitionAdjustments = async (
  team: string,
  season: string = '2024-25',
  adjustmentPercentage: number = 5.0
): Promise<Blob> => {
  const response = await api.post('/generate-adjustments', {
    team,
    season,
    adjustment_percentage: adjustmentPercentage
  }, {
    responseType: 'blob'
  });
  return response.data;
};

