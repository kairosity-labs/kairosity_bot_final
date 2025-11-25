import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Bot, Brain, Search, FileText, Activity } from 'lucide-react';
import TraceItem from './TraceItem';

const AgentAccordion = ({ agent, index }) => {
    const [isOpen, setIsOpen] = useState(false);

    const getAgentIcon = () => {
        if (agent.name.includes('Retrieval')) return <Search className="w-4 h-4 text-green-400" />;
        if (agent.name.includes('Analyst')) return <Brain className="w-4 h-4 text-blue-400" />;
        if (agent.name.includes('Supervisor')) return <FileText className="w-4 h-4 text-purple-400" />;
        return <Bot className="w-4 h-4 text-gray-400" />;
    };

    const getAgentColor = () => {
        if (agent.name.includes('Retrieval')) return 'border-green-500/30 bg-green-500/10';
        if (agent.name.includes('Analyst')) return 'border-blue-500/30 bg-blue-500/10';
        if (agent.name.includes('Supervisor')) return 'border-purple-500/30 bg-purple-500/10';
        return 'border-gray-500/30 bg-gray-500/10';
    };

    return (
        <div className="mb-2">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`w-full flex items-center justify-between p-3 rounded-lg border ${getAgentColor()} hover:brightness-110`}
            >
                <div className="flex items-center gap-2">
                    {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    {getAgentIcon()}
                    <span className="font-medium text-sm">{agent.name}</span>
                </div>
                <span className="text-xs text-gray-400">{agent.traces.length} events</span>
            </button>

            {isOpen && (
                <div className="mt-2 ml-6 space-y-1">
                    {agent.traces.map((trace) => (
                        <TraceItem key={trace.id} trace={trace} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default AgentAccordion;
