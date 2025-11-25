import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Clock, Target } from 'lucide-react';
import AgentAccordion from './AgentAccordion';

const PhaseAccordion = ({ phase, index }) => {
    const [isOpen, setIsOpen] = useState(index === 0); // First phase open by default

    const duration = new Date(phase.endTime) - new Date(phase.startTime);
    const durationSec = (duration / 1000).toFixed(1);

    return (
        <div className="mb-3">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-blue-600/20 to-purple-600/20 hover:from-blue-600/30 hover:to-purple-600/30 rounded-lg border border-blue-500/30 hover-lift"
            >
                <div className="flex items-center gap-3">
                    {isOpen ? <ChevronDown className="w-5 h-5 text-blue-400" /> : <ChevronRight className="w-5 h-5 text-blue-400" />}
                    <Target className="w-5 h-5 text-purple-400" />
                    <span className="font-semibold text-lg">{phase.name}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                    <div className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        <span>{durationSec}s</span>
                    </div>
                    <span>{phase.agents.length} agents</span>
                </div>
            </button>

            {isOpen && (
                <div className="mt-2 ml-8 space-y-2">
                    {phase.agents.map((agent, idx) => (
                        <AgentAccordion key={agent.id} agent={agent} index={idx} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default PhaseAccordion;
