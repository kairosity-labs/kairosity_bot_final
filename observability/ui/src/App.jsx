import React, { useState, useEffect } from 'react';
import { Activity, ChevronDown, Layout, RefreshCw } from 'lucide-react';
import { buildWorkflowHierarchy, buildGraphData } from './utils/hierarchyBuilder';
import GraphView from './components/graph/GraphView';
import EventCard from './components/EventCard';
import ResearchStage from './components/ResearchStage';
import CommunityStage from './components/CommunityStage';
import ConsensusStage from './components/ConsensusStage';

const API_BASE = 'http://localhost:8000';

function App() {
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [events, setEvents] = useState([]);
  const [stages, setStages] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [viewMode, setViewMode] = useState('split');
  const [wsConnected, setWsConnected] = useState(false);
  const [runStatus, setRunStatus] = useState('complete');
  const [isRefreshing, setIsRefreshing] = useState(false); // 'split' or 'list'

  // Fetch runs
  useEffect(() => {
    fetch(`${API_BASE}/runs`)
      .then(res => res.json())
      .then(data => {
        setRuns(data);
        if (data.length > 0) setSelectedRun(data[0]);
      })
      .catch(err => console.error("Failed to fetch runs:", err));
  }, []);

  // Fetch events
  useEffect(() => {
    if (selectedRun) {
      fetch(`${API_BASE}/runs/${selectedRun}/events`)
        .then(res => res.json())
        .then(data => {
          setEvents(data);
        })
        .catch(err => console.error("Failed to fetch events:", err));
    }
  }, [selectedRun]);

  // WebSocket connection for live updates
  useEffect(() => {
    if (!selectedRun) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/runs/${selectedRun}`);

    ws.onopen = () => setWsConnected(true);

    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data);
      if (data.type === 'new_event') {
        setEvents(prev => [...prev, data.event]);
      }
    };

    ws.onclose = () => setWsConnected(false);

    return () => ws.close();
  }, [selectedRun]);

  // Auto-rebuild graph/hierarchy when events change
  useEffect(() => {
    if (events.length > 0) {
      setStages(buildWorkflowHierarchy(events));
      setGraphData(buildGraphData(events));
    }
  }, [events]);

  // Fetch run status
  useEffect(() => {
    if (!selectedRun) return;

    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/runs/${selectedRun}/status`);
        const data = await res.json();
        setRunStatus(data.status);
      } catch (err) {
        console.error("Failed to fetch status:", err);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, [selectedRun]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/runs/${selectedRun}/events`);
      const data = await res.json();
      setEvents(data);
    } catch (err) {
      console.error("Failed to refresh:", err);
    }
    setIsRefreshing(false);
  };

  return (
    <div className="flex flex-col h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] overflow-hidden">
      {/* Top Navigation Bar */}
      <div className="h-16 border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)] flex items-center px-8 justify-between">
        <div className="flex items-center gap-8">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-[var(--accent-research)]" />
            <span className="font-bold text-xl text-white">Observability</span>
          </div>

          {/* Divider */}
          <div className="h-10 w-px bg-[var(--border-subtle)]" />

          {/* Live Indicator */}
          <div className="flex items-center gap-3 px-4 py-2 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-subtle)]">
            <div className={`w-2.5 h-2.5 rounded-full ${runStatus === 'active' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
            <span className="text-sm font-medium text-white">
              {runStatus === 'active' ? 'Live' : 'Complete'}
            </span>
          </div>

          {/* WebSocket Status */}
          {runStatus === 'active' && (
            <div className="flex items-center gap-3 px-4 py-2 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-subtle)]">
              <div className={`w-2.5 h-2.5 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-white">
                {wsConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          )}

          {/* Divider */}
          <div className="h-10 w-px bg-[var(--border-subtle)]" />

          {/* Run Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center gap-3 px-5 py-2 bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg text-sm hover:border-[var(--border-emphasis)] transition-all hover:bg-[var(--bg-card)]"
            >
              <span className="text-gray-400 text-xs uppercase tracking-wider">Run:</span>
              <span className="font-medium text-white">{selectedRun || 'Select Run'}</span>
              <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-[90]"
                  onClick={() => setIsDropdownOpen(false)}
                />
                <div className="absolute top-full left-0 mt-2 w-72 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-lg shadow-xl z-[100] max-h-96 overflow-y-auto">
                  {runs.map(run => (
                    <button
                      key={run}
                      onClick={() => {
                        setSelectedRun(run);
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full text-left px-4 py-2.5 text-sm hover:bg-[var(--bg-tertiary)] transition-colors ${selectedRun === run ? 'text-[var(--accent-research)] font-medium bg-[var(--bg-tertiary)]/50' : 'text-white'}`}
                    >
                      {run}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-6">
          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-3 hover:bg-[var(--bg-tertiary)] rounded-lg transition-all disabled:opacity-50 border border-transparent hover:border-[var(--border-subtle)]"
            title="Refresh events"
          >
            <RefreshCw className={`w-5 h-5 text-white ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>

          {/* Divider */}
          <div className="h-10 w-px bg-[var(--border-subtle)]" />

          {/* View Toggle */}
          <div className="flex bg-[var(--bg-primary)] rounded-lg p-1.5 border border-[var(--border-subtle)] gap-1.5">
            <button
              onClick={() => setViewMode('split')}
              className={`px-5 py-2 text-sm rounded-md transition-all font-medium ${viewMode === 'split' ? 'bg-[var(--accent-research)] text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-[var(--bg-tertiary)]'}`}
            >
              Graph + Details
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-5 py-2 text-sm rounded-md transition-all font-medium ${viewMode === 'list' ? 'bg-[var(--accent-research)] text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-[var(--bg-tertiary)]'}`}
            >
              Hierarchy List
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">

        {/* Left Pane: Graph View (only in split mode) */}
        {viewMode === 'split' && (
          <div className="w-2/3 border-r border-[var(--border-subtle)] relative">
            <GraphView
              data={graphData}
              onNodeClick={(event) => setSelectedEvent(event)}
            />
            <div className="absolute top-4 left-4 bg-[var(--bg-card)]/80 backdrop-blur px-3 py-1.5 rounded border border-[var(--border-subtle)] text-xs text-[var(--text-muted)]">
              Click nodes to view details
            </div>
          </div>
        )}

        {/* Right Pane: Details / List */}
        <div className={`${viewMode === 'split' ? 'w-1/3' : 'w-full'} flex flex-col bg-[var(--bg-primary)]`}>

          {viewMode === 'split' ? (
            // Detail View
            <div className="flex-1 overflow-y-auto p-6">
              {selectedEvent ? (
                <div>
                  <div className="mb-6 pb-4 border-b border-[var(--border-subtle)]">
                    <div className="text-xs font-bold text-[var(--text-muted)] uppercase tracking-wider mb-1">
                      Selected Event
                    </div>
                    <h2 className="text-xl font-bold capitalize text-[var(--text-primary)]">
                      {selectedEvent.event_type.replace('_', ' ')}
                    </h2>
                    <div className="text-sm text-[var(--text-secondary)] mt-1">
                      Source: {selectedEvent.source}
                    </div>
                  </div>
                  <EventCard event={selectedEvent} isOpenDefault={true} />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-[var(--text-muted)]">
                  <Layout className="w-12 h-12 mb-4 opacity-20" />
                  <p>Select a node from the graph</p>
                  <p className="text-xs mt-2">or switch to List View</p>
                </div>
              )}
            </div>
          ) : (
            // Hierarchy List View
            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-4xl mx-auto">
                {stages.map((stage) => {
                  if (stage.type === 'research') return <ResearchStage key={stage.id} stage={stage} />;
                  if (stage.type === 'community') return <CommunityStage key={stage.id} stage={stage} />;
                  if (stage.type === 'consensus') return <ConsensusStage key={stage.id} stage={stage} />;
                  return null;
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
