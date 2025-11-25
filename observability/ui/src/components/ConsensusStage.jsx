import React, { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle } from 'lucide-react';
import EventCard from './EventCard';

const ConsensusStage = ({ stage }) => {
    const [isOpen, setIsOpen] = useState(true);

    return (
        <div className="mb-6">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full glass-strong p-5 rounded-lg hover:brightness-110 transition-all"
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {isOpen ? (
                            <ChevronDown className="w-5 h-5 text-[var(--accent-consensus)]" />
                        ) : (
                            <ChevronRight className="w-5 h-5 text-[var(--accent-consensus)]" />
                        )}
                        <CheckCircle className="w-6 h-6 text-[var(--accent-consensus)]" />
                        <span className="text-lg font-semibold gradient-text-consensus">
                            {stage.name}
                        </span>
                    </div>
                    <span className="text-sm text-[var(--text-muted)]">{stage.events.length} events</span>
                </div>
            </button>

            {isOpen && (
                <div className="mt-4 ml-8 space-y-2">
                    {stage.events.map(event => (
                        <EventCard key={event._index} event={event} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default ConsensusStage;
