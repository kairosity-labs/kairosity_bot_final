import React, { useState } from 'react';
import { MessageSquare, Search, FileText, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react';
import TraceDetails from './TraceDetails';

const TraceItem = ({ trace }) => {
    const [isOpen, setIsOpen] = useState(false);

    const getTypeIcon = () => {
        if (trace.type === 'reasoning') return <MessageSquare className="w-3 h-3 text-blue-300" />;
        if (trace.type === 'search_result') return <Search className="w-3 h-3 text-green-300" />;
        if (trace.type === 'summary' || trace.type === 'analysis') return <FileText className="w-3 h-3 text-purple-300" />;
        return <AlertCircle className="w-3 h-3 text-gray-300" />;
    };

    const getTypeColor = () => {
        if (trace.type === 'reasoning') return 'border-blue-400/20 bg-blue-400/5';
        if (trace.type === 'search_result') return 'border-green-400/20 bg-green-400/5';
        if (trace.type === 'summary' || trace.type === 'analysis') return 'border-purple-400/20 bg-purple-400/5';
        return 'border-gray-400/20 bg-gray-400/5';
    };

    const formatTime = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };

    return (
        <div className="mb-1">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded border ${getTypeColor()} hover:brightness-110 text-left`}
            >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                    {isOpen ? <ChevronDown className="w-3 h-3 flex-shrink-0" /> : <ChevronRight className="w-3 h-3 flex-shrink-0" />}
                    {getTypeIcon()}
                    <span className="text-xs font-medium truncate">{trace.type}</span>
                </div>
                <span className="text-xs text-gray-500 ml-2 flex-shrink-0">{formatTime(trace.timestamp)}</span>
            </button>

            {isOpen && (
                <div className="mt-1 ml-5">
                    <TraceDetails data={trace.data} />
                </div>
            )}
        </div>
    );
};

export default TraceItem;
