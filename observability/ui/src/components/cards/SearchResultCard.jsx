import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Search, ExternalLink } from 'lucide-react';

const SearchResultCard = ({ label, value }) => {
    const [isOpen, setIsOpen] = useState(value.length <= 5);

    const source = value[0]?.source || 'unknown';

    const getSourceColor = () => {
        if (source.includes('google')) return 'bg-blue-500/20 text-blue-300';
        if (source.includes('perplexity')) return 'bg-purple-500/20 text-purple-300';
        if (source.includes('duckduckgo')) return 'bg-orange-500/20 text-orange-300';
        return 'bg-green-500/20 text-green-300';
    };

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
                    <Search className="w-4 h-4 text-green-400" />
                    <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                        {label}
                    </span>
                    <span className={`px-2 py-0.5 text-xs rounded ${getSourceColor()}`}>
                        {value.length} results • {source.replace('_', ' ')}
                    </span>
                </div>
            </button>

            {isOpen && (
                <div className="space-y-2 mt-2">
                    {value.map((result, idx) => (
                        <div
                            key={idx}
                            className="border border-[var(--border-subtle)] rounded-lg p-3 hover:border-[var(--border-emphasis)] transition-colors"
                        >
                            <div className="flex items-start justify-between gap-2 mb-1">
                                <h4 className="text-sm font-medium text-[var(--text-primary)] line-clamp-2">
                                    {result.title || 'Untitled'}
                                </h4>
                                <span className="text-xs text-[var(--text-muted)] shrink-0">
                                    #{idx + 1}
                                </span>
                            </div>

                            <a
                                href={result.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mb-2 group"
                            >
                                <span className="truncate">{result.url}</span>
                                <ExternalLink className="w-3 h-3 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </a>

                            {result.content && (
                                <p className="text-xs text-[var(--text-secondary)] line-clamp-3">
                                    {result.content}
                                </p>
                            )}

                            <div className="flex items-center gap-3 mt-2 text-xs text-[var(--text-muted)]">
                                {result.date && result.date !== 'Unknown' && (
                                    <span>📅 {result.date}</span>
                                )}
                                {result.domain && (
                                    <span>🌐 {result.domain}</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default SearchResultCard;
