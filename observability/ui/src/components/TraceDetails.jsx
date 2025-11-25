import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ExternalLink, Copy, Check } from 'lucide-react';

const TraceDetails = ({ data }) => {
    const [copiedField, setCopiedField] = useState(null);

    const copyToClipboard = (text, field) => {
        navigator.clipboard.writeText(text);
        setCopiedField(field);
        setTimeout(() => setCopiedField(null), 2000);
    };

    const renderContent = (content, fieldName) => {
        try {
            if (typeof content === 'string') {
                return (
                    <div className="relative group">
                        <button
                            onClick={() => copyToClipboard(content, fieldName)}
                            className="absolute top-2 right-2 p-1.5 bg-gray-800/80 hover:bg-gray-700 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Copy"
                        >
                            {copiedField === fieldName ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                        </button>
                        <div className="prose prose-invert prose-sm max-w-none prose-p:text-gray-300 prose-headings:text-gray-100 prose-code:text-blue-300">
                            <ReactMarkdown>{content}</ReactMarkdown>
                        </div>
                    </div>
                );
            }
            if (Array.isArray(content)) {
                return (
                    <div className="space-y-3">
                        {content.map((item, i) => (
                            <div key={i} className="p-3 bg-gray-900/50 rounded-lg border border-gray-800">
                                {item.content && (
                                    <div className="prose prose-invert prose-sm max-w-none prose-p:text-gray-300 prose-code:text-blue-300 mb-2">
                                        <ReactMarkdown>{item.content}</ReactMarkdown>
                                    </div>
                                )}
                                {item.citations && item.citations.length > 0 && (
                                    <div className="flex flex-wrap gap-2 mt-2">
                                        {item.citations.map((url, j) => (
                                            <a
                                                key={j}
                                                href={url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-1 text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded hover:bg-blue-500/30 transition-colors"
                                            >
                                                <ExternalLink className="w-3 h-3" />
                                                Source {j + 1}
                                            </a>
                                        ))}
                                    </div>
                                )}
                                {!item.content && !item.citations && (
                                    <pre className="text-xs overflow-x-auto text-gray-400">{JSON.stringify(item, null, 2)}</pre>
                                )}
                            </div>
                        ))}
                    </div>
                );
            }
            return (
                <pre className="text-xs overflow-x-auto bg-gray-900/50 p-3 rounded border border-gray-800 text-gray-300">
                    {JSON.stringify(content, null, 2)}
                </pre>
            );
        } catch (error) {
            return <pre className="text-xs text-red-400 bg-red-900/20 p-3 rounded">Error: {error.message}</pre>;
        }
    };

    return (
        <div className="space-y-4 p-4 bg-gray-900/30 rounded-lg border border-gray-800">
            {data.input && (
                <div>
                    <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2 flex items-center gap-2">
                        <span className="w-1 h-4 bg-blue-500 rounded"></span>
                        Input
                    </h4>
                    <div className="ml-3">{renderContent(data.input, 'input')}</div>
                </div>
            )}

            {data.output && (
                <div>
                    <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2 flex items-center gap-2">
                        <span className="w-1 h-4 bg-green-500 rounded"></span>
                        Output
                    </h4>
                    <div className="ml-3">{renderContent(data.output, 'output')}</div>
                </div>
            )}
        </div>
    );
};

export default TraceDetails;
