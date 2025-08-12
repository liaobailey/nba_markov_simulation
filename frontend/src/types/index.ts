export interface GameData {
  game: number;
  expected_wins: number;
  team_score: number;
  opp_score: number;
  is_win: boolean;
}

export interface SeasonData {
  season: number;
  games: GameData[];
  final_expected_wins: number;
  total_wins: number;
  win_percentage: number;
}

export interface SimulationStatistics {
  average_expected_wins: number;
  standard_deviation: number;
  confidence_interval_95: number;
  min_wins: number;
  max_wins: number;
}

export interface SimulationResult {
  seasons: SeasonData[];
  statistics: SimulationStatistics;
}

export interface Team {
  team: string;
}

export const TEAM_WINS: Record<string, number> = {
  "ATL": 40,
  "BKN": 26,
  "BOS": 61,
  "CHA": 19,
  "CHI": 39,
  "CLE": 64,
  "DAL": 39,
  "DEN": 50,
  "DET": 44,
  "GSW": 48,
  "HOU": 52,
  "IND": 50,
  "LAC": 50,
  "LAL": 50,
  "MEM": 48,
  "MIA": 37,
  "MIL": 48,
  "MIN": 49,
  "NOP": 21,
  "NYK": 51,
  "OKC": 68,
  "ORL": 41,
  "PHI": 24,
  "PHX": 36,
  "POR": 36,
  "SAC": 40,
  "SAS": 34,
  "TOR": 30,
  "UTA": 17,
  "WAS": 18,
};

