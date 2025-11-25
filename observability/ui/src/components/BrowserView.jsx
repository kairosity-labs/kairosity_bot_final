import React, { useState } from 'react';
import { X, RefreshCw, ExternalLink } from 'lucide-react';

const BrowserView = ({ url, onClose }) => {
    const [loading, setLoading] = useState(true);

    // Use our proxy endpoint
    const proxyUrl = `http://localhost:8000/proxy?url=${encodeURIComponent(url)}`;

    return (
        <div className="absolute inset-0 z-20 flex flex-col bg-background/95 backdrop-blur-sm p-4">
            <div className="bg-surface border border-gray-700 rounded-lg shadow-2xl flex flex-col flex-1 overflow-hidden">
                {/* Browser Bar */}
                <div className="h-12 bg-surface border-b border-gray-700 flex items-center px-4 gap-4">
                    <div className="flex-1 bg-background h-8 rounded flex items-center px-3 text-sm text-gray-400 truncate font-mono">
                        {url}
                    </div>
                    <div className="flex items-center gap-2">
                        <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                            title="Open in real browser"
                        >
                            <ExternalLink className="w-4 h-4" />
                        </a>
                        <button
                            onClick={() => setLoading(true)}
                            className="p-2 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                            title="Refresh"
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        </button>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-red-500/20 hover:text-red-400 rounded text-gray-400"
                            title="Close"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 relative bg-white">
                    {loading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-surface/50 z-10">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                        </div>
                    )}
                    <iframe
                        src={proxyUrl}
                        className="w-full h-full border-none"
                        onLoad={() => setLoading(false)}
                        sandbox="allow-same-origin allow-scripts"
                        title="Embedded Browser"
                    />
                </div>
            </div>
        </div>
    );
};

export default BrowserView;
