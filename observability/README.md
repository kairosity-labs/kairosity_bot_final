# AG Observability UI

A local web interface to visualize and inspect the execution of the AGForecast bot.

## Features
- **Graph Visualization**: See the flow of agents, reasoning, and tool calls.
- **Node Inspection**: Click on any node to see detailed inputs, outputs, and logs.
- **Embedded Browser**: View source citations directly within the app (via a local proxy to bypass some iframe restrictions).
- **Dark Mode**: Premium aesthetic inspired by modern dev tools.

## Prerequisites
- Node.js & npm
- Python 3.11+ (and the `venv_kairosity` virtual environment)

## How to Run

You need to run the Backend and Frontend in separate terminals.

### 1. Start the Backend (FastAPI)
This server reads the logs from `kairosity_bot_final/logs` and serves them to the UI.

```bash
cd kairosity_bot_final
./venv_kairosity/bin/python observability/server/main.py
```
*Server runs on http://localhost:8000*

### 2. Start the Frontend (React + Vite)
This is the web interface.

```bash
cd kairosity_bot_final/observability/ui
npm run dev
```
*UI runs on http://localhost:5173*

## Usage
1. Open http://localhost:5173 in your browser.
2. Select a **Run ID** from the sidebar (e.g., `run_20251125_...`).
3. Explore the graph. Click nodes to see details in the right panel.
4. Click "Source" buttons in the details panel to open the embedded browser.
