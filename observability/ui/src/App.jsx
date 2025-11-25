import React, { useState, useEffect } from 'react';
import { Activity, ChevronDown, Layout } from 'lucide-react';
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
  const [viewMode, setViewMode] = useState('split'); // 'split' or 'list'

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
          setStages(buildWorkflowHierarchy(data));
          setGraphData(buildGraphData(data));
        })
        .catch(err => console.error("Failed to fetch events:", err));
    }
  }, [selectedRun]);

  return (
    <div className="flex flex-col h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] overflow-hidden">
      {/* Top Navigation Bar */}
      <div className="h-14 border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)] flex items-center px-4 justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-[var(--accent-research)]" />
            <span className="font-bold text-lg gradient-text-research">Observability</span>
          </div>

          {/* Run Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-md text-sm hover:border-[var(--border-emphasis)] transition-colors"
            >
              <span className="text-[var(--text-muted)]">Run:</span>
              <span className="font-medium">{selectedRun || 'Select Run'}</span>
              <ChevronDown className={`w-4 h-4 text-[var(--text-muted)] transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-[90]"
                  onClick={() => setIsDropdownOpen(false)}
                />
                <div className="absolute top-full left-0 mt-1 w-64 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-md shadow-xl z-[100] max-h-96 overflow-y-auto">
                  {runs.map(run => (
                    <button
                      key={run}
                      onClick={() => {
                        setSelectedRun(run);
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full text-left px-4 py-2 text-sm hover:bg-[var(--bg-tertiary)] ${selectedRun === run ? 'text-[var(--accent-research)] font-medium' : ''}`}
                    >
                      {run}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* View Toggle */}
        <div className="flex bg-[var(--bg-card)] rounded-md p-1 border border-[var(--border-subtle)]">
          <button
            onClick={() => setViewMode('split')}
            className={`px-3 py-1 text-xs rounded ${viewMode === 'split' ? 'bg-[var(--bg-tertiary)] text-white' : 'text-[var(--text-muted)] hover:text-white'}`}
          >
            Graph + Details
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-3 py-1 text-xs rounded ${viewMode === 'list' ? 'bg-[var(--bg-tertiary)] text-white' : 'text-[var(--text-muted)] hover:text-white'}`}
          >
            Hierarchy List
          </button>
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
