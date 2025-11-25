import React, { useState } from 'react';
import { ChevronDown, ChevronRight, List } from 'lucide-react';
import JsonCard from './JsonCard';

const ArrayCard = ({ label, value }) => {
    const [isOpen, setIsOpen] = useState(value.length <= 3); // Auto-open if 3 or fewer items

    return (
        <div className="card p-4 mb-3">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between mb-2"
            >
                <div className="flex items-center gap-2">
                    {isOpen ? (
                        <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
                    ) : (
                        <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
                    )}
                    <List className="w-4 h-4 text-green-400" />
                    <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                        {label}
                    </span>
                    <span className="px-2 py-0.5 bg-green-500/20 text-green-300 text-xs rounded">
                        {value.length} items
                    </span>
                </div>
            </button>

            {isOpen && (
                <div className="ml-4 mt-2 space-y-2">
                    {value.map((item, index) => (
                        <div key={index} className="border-l-2 border-[var(--border-subtle)] pl-3">
                            <JsonCard label={`Item ${index + 1}`} value={item} nested />
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ArrayCard;
