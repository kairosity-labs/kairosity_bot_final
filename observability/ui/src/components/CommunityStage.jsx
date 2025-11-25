import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Users, Clock } from 'lucide-react';
import AgentSection from './AgentSection';

const CommunityStage = ({ stage }) => {
    const [isOpen, setIsOpen] = useState(true);

    const duration = stage.endTime && stage.startTime ?
        ((new Date(stage.endTime) - new Date(stage.startTime)) / 1000).toFixed(1) :
        '0';

    return (
        <div className="mb-6">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full glass-strong p-5 rounded-lg hover:brightness-110 transition-all"
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {isOpen ? (
                            <ChevronDown className="w-5 h-5 text-[var(--accent-community)]" />
                        ) : (
                            <ChevronRight className="w-5 h-5 text-[var(--accent-community)]" />
                        )}
                        <Users className="w-6 h-6 text-[var(--accent-community)]" />
                        <span className="text-lg font-semibold gradient-text-community">
                            {stage.name}
                        </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-[var(--text-muted)]">
                        <div className="flex items-center gap-1.5">
                            <Clock className="w-4 h-4" />
                            <span>{duration}s</span>
                        </div>
                        <span>{stage.researchers.length} researchers</span>
                    </div>
                </div>
            </button>

            {isOpen && (
                <div className="mt-4 ml-8 space-y-3">
                    {stage.researchers.map(researcher => (
                        <AgentSection
                            key={researcher.name}
                            name={researcher.name}
                            events={researcher.events}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export default CommunityStage;
