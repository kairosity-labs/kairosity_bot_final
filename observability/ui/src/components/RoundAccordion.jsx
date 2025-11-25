import React, { useState } from 'react';
import { ChevronDown, ChevronRight, RotateCw } from 'lucide-react';
import AgentSection from './AgentSection';

const RoundAccordion = ({ round, index }) => {
    const [isOpen, setIsOpen] = useState(index === 0); // First round open by default

    const agentNames = Object.keys(round.agents);
    const totalEvents = agentNames.reduce((sum, name) => sum + round.agents[name].length, 0);

    return (
        <div className="card p-4 border-l-4 border-[var(--accent-research)]">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between"
            >
                <div className="flex items-center gap-2">
                    {isOpen ? (
                        <ChevronDown className="w-4 h-4" />
                    ) : (
                        <ChevronRight className="w-4 h-4" />
                    )}
                    <RotateCw className="w-4 h-4 text-[var(--accent-research)]" />
                    <span className="font-semibold">Round {round.number}</span>
                </div>
                <div className="text-xs text-[var(--text-muted)]">
                    {agentNames.length} agents • {totalEvents} events
                </div>
            </button>

            {isOpen && (
                <div className="mt-4 space-y-3">
                    {agentNames.map(agentName => (
                        <AgentSection
                            key={agentName}
                            name={agentName}
                            events={round.agents[agentName]}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export default RoundAccordion;
