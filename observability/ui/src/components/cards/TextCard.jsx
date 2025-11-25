import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Check } from 'lucide-react';

const TextCard = ({ label, value }) => {
    const [copied, setCopied] = useState(false);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="card p-4 mb-3">
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                        {label}
                    </span>
                    <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-xs rounded">
                        Text
                    </span>
                </div>
                <button
                    onClick={copyToClipboard}
                    className="p-1.5 hover:bg-[var(--bg-tertiary)] rounded transition-colors"
                    title="Copy to clipboard"
                >
                    {copied ? (
                        <Check className="w-4 h-4 text-green-400" />
                    ) : (
                        <Copy className="w-4 h-4 text-[var(--text-muted)]" />
                    )}
                </button>
            </div>
            <div className="prose prose-sm">
                <ReactMarkdown>{value}</ReactMarkdown>
            </div>
        </div>
    );
};

export default TextCard;
