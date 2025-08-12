# NBA Markov Basketball Simulation

A web application that simulates NBA team win totals using Markov chain models based on possession-level basketball statistics.

## Features

- **Team Selection**: Choose from all 30 NBA teams
- **Season Simulation**: Simulate multiple 82-game seasons
- **Live Visualization**: Watch convergence lines as seasons complete
- **Statistical Analysis**: View average expected wins, standard deviation, and confidence intervals
- **Real-time Results**: See how changing parameters affects simulated outcomes

## Architecture

- **Backend**: FastAPI with Python, using DuckDB for data storage
- **Frontend**: React with TypeScript, Material-UI for components, Recharts for visualizations
- **Simulation Engine**: Markov chain models based on transition matrices

## Prerequisites

- Python 3.8+
- Node.js 16+
- The NBA database file at `../PycharmProjects/cleannbadata/nba_clean.db`

## Quick Start

### 1. Start the Backend

```bash
./start_backend.sh
```

The backend will be available at http://localhost:8000

### 2. Start the Frontend

In a new terminal:

```bash
./start_frontend.sh
```

The frontend will be available at http://localhost:3000

## Manual Setup

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

## API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /api/teams` - Get list of available teams
- `POST /api/simulate` - Run simulation for a team

## Usage

1. Select a team from the dropdown
2. Choose the number of seasons to simulate (default: 10)
3. Click "Simulate" to start the simulation
4. Watch as each season's convergence line appears on the chart
5. View the final statistics including average expected wins and confidence intervals

## Design Choices

- **Typography**: Archivo font family for modern, clean appearance
- **Color Scheme**: Deep blue header (#1e3a8a) matching the nba_web_app design
- **Layout**: Material-UI components with responsive design
- **Visualization**: Recharts for interactive line charts showing convergence

## Project Structure

```
markovbasketball/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   └── simulation.py    # Markov simulation logic
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── api/            # API service
│   │   ├── types/          # TypeScript definitions
│   │   └── App.tsx         # Main application
│   └── package.json
├── start_backend.sh
├── start_frontend.sh
└── README.md
```

## Database Schema

The application expects a DuckDB database with a table `agg_team_txn_cnts` containing:
- `team`: Team abbreviation
- `state`: Current game state
- `next_state`: Next game state
- `count`: Transition count
- `poss_per_game`: Possessions per game

## Future Enhancements

- Parameter adjustment sliders (shooting %, turnovers, etc.)
- Real-time game-by-game streaming
- Historical comparison features
- Export simulation results



