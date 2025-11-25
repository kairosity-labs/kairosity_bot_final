import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Target, Clock } from 'lucide-react';
import RoundAccordion from './RoundAccordion';

const ResearchStage = ({ stage }) => {
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
                            <ChevronDown className="w-5 h-5 text-[var(--accent-research)]" />
                        ) : (
                            <ChevronRight className="w-5 h-5 text-[var(--accent-research)]" />
                        )}
                        <Target className="w-6 h-6 text-[var(--accent-research)]" />
                        <span className="text-lg font-semibold gradient-text-research">
                            {stage.name}
                        </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-[var(--text-muted)]">
                        <div className="flex items-center gap-1.5">
                            <Clock className="w-4 h-4" />
                            <span>{duration}s</span>
                        </div>
                        <span>{stage.rounds.length} rounds</span>
                    </div>
                </div>
            </button>

            {isOpen && (
                <div className="mt-4 ml-8 space-y-3">
                    {stage.rounds.map((round, idx) => (
                        <RoundAccordion key={round.number} round={round} index={idx} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default ResearchStage;
