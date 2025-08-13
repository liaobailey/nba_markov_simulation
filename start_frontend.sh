#!/bin/bash

echo "Starting NBA Markov Simulation Frontend..."

# Check if node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Start the development server
echo "Starting React development server..."
cd frontend
npm start



