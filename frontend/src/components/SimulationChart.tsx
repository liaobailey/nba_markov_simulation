import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { SeasonData } from '../types';

interface SimulationChartProps {
  seasons: SeasonData[];
  selectedTeam: string;
}

const SimulationChart: React.FC<SimulationChartProps> = ({ seasons, selectedTeam }) => {
  // Transform data for Recharts - create one data point per game number
  const gameNumbers = Array.from({ length: 82 }, (_, i) => i + 1);
  
  const chartData = gameNumbers.map(gameNum => {
    const dataPoint: any = { game: gameNum };
    
    // Add expected wins for each season at this game number
    seasons.forEach(season => {
      const gameData = season.games.find(game => game.game === gameNum);
      if (gameData) {
        dataPoint[`Season ${season.season}`] = gameData.expected_wins;
      }
    });
    
    return dataPoint;
  });

  // Generate colors for each season
  const colors = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
  ];

  return (
    <ResponsiveContainer width="100%" height={500}>
      <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 25 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          dataKey="game" 
          label={{ value: 'Games in Season', position: 'insideBottom', offset: -5 }}
          type="number"
          domain={[1, 82]}
        />
        <YAxis 
          label={{ value: 'Expected Wins', angle: -90, position: 'insideLeft' }}
          domain={[0, 82]}
        />
        <Tooltip 
          formatter={(value: number, name: string) => [value?.toFixed(1) || 'N/A', name]}
          labelFormatter={(label) => `Game ${label}`}
        />
        {seasons.map((season, index) => (
          <Line
            key={season.season}
            type="monotone"
            dataKey={`Season ${season.season}`}
            stroke={colors[index % colors.length]}
            strokeWidth={1.5}
            dot={false}
            connectNulls={true}
            opacity={0.8}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
};

export default SimulationChart;

