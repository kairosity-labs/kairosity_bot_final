import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Bot, Search, FileText, Eye } from 'lucide-react';
import EventCard from './EventCard';

const AgentSection = ({ name, events }) => {
    const [isOpen, setIsOpen] = useState(false);

    const getAgentIcon = () => {
        if (name.includes('Retrieval')) return <Search className="w-4 h-4 text-green-400" />;
        if (name.includes('Analyst')) return <FileText className="w-4 h-4 text-blue-400" />;
        if (name.includes('Supervisor')) return <Eye className="w-4 h-4 text-purple-400" />;
        return <Bot className="w-4 h-4 text-gray-400" />;
    };

    const getAgentColor = () => {
        if (name.includes('Retrieval')) return 'border-green-500/30 bg-green-500/5';
        if (name.includes('Analyst')) return 'border-blue-500/30 bg-blue-500/5';
        if (name.includes('Supervisor')) return 'border-purple-500/30 bg-purple-500/5';
        return 'border-[var(--border-subtle)] bg-[var(--bg-card)]';
    };

    return (
        <div className={`border rounded-lg ${getAgentColor()}`}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full px-4 py-3 flex items-center justify-between hover:brightness-110 transition-all"
            >
                <div className="flex items-center gap-2">
                    {isOpen ? (
                        <ChevronDown className="w-4 h-4" />
                    ) : (
                        <ChevronRight className="w-4 h-4" />
                    )}
                    {getAgentIcon()}
                    <span className="text-sm font-medium">{name}</span>
                </div>
                <span className="text-xs text-[var(--text-muted)]">{events.length} events</span>
            </button>

            {isOpen && (
                <div className="px-4 pb-4 space-y-2">
                    {events.map(event => (
                        <EventCard key={event._index} event={event} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default AgentSection;
