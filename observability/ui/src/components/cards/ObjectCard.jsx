import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Braces } from 'lucide-react';
import JsonCard from './JsonCard';

const ObjectCard = ({ label, value, nested = false }) => {
    const keys = Object.keys(value);
    const [isOpen, setIsOpen] = useState(!nested || keys.length <= 3);

    return (
        <div className={`${nested ? '' : 'card p-4 mb-3'}`}>
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
                    <Braces className="w-4 h-4 text-orange-400" />
                    <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                        {label}
                    </span>
                    <span className="px-2 py-0.5 bg-orange-500/20 text-orange-300 text-xs rounded">
                        {keys.length} fields
                    </span>
                </div>
            </button>

            {isOpen && (
                <div className={`${nested ? 'ml-4' : 'ml-2'} mt-2 space-y-2`}>
                    {keys.map((key) => (
                        <div key={key} className="border-l-2 border-[var(--border-subtle)] pl-3">
                            <JsonCard label={key} value={value[key]} nested />
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ObjectCard;
