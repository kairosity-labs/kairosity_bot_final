import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Clock } from 'lucide-react';
import JsonCard from './cards/JsonCard';

const EventCard = ({ event, isOpenDefault = false }) => {
    const [isOpen, setIsOpen] = useState(isOpenDefault);

    const formatTime = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            fractionalSecondDigits: 1
        });
    };

    const getEventColor = (type) => {
        switch (type) {
            case 'reasoning': return 'border-blue-400/30 bg-blue-400/5';
            case 'search_result': return 'border-green-400/30 bg-green-400/5';
            case 'analysis': return 'border-purple-400/30 bg-purple-400/5';
            case 'review': return 'border-orange-400/30 bg-orange-400/5';
            case 'prediction': return 'border-pink-400/30 bg-pink-400/5';
            case 'summary': return 'border-cyan-400/30 bg-cyan-400/5';
            default: return 'border-[var(--border-subtle)] bg-[var(--bg-card)]';
        }
    };

    return (
        <div className={`border rounded-lg mb-2 ${getEventColor(event.event_type)}`}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-3">
                    {isOpen ? (
                        <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
                    ) : (
                        <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
                    )}
                    <span className="text-sm font-medium capitalize">{event.event_type.replace('_', ' ')}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                    <Clock className="w-3 h-3" />
                    <span>{formatTime(event.timestamp)}</span>
                </div>
            </button>

            {isOpen && (
                <div className="px-4 pb-4 space-y-3">
                    {event.input && (
                        <div>
                            <JsonCard label="input" value={event.input} />
                        </div>
                    )}
                    {event.output && (
                        <div>
                            <JsonCard label="output" value={event.output} />
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default EventCard;
