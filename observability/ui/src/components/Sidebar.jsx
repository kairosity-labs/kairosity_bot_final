import React from 'react';
import ReactMarkdown from 'react-markdown';
import { X, ExternalLink, Activity, Search, FileText, Brain } from 'lucide-react';

const Sidebar = ({ node, onClose, onOpenUrl }) => {
  if (!node) return null;

  const { event_type, source, input, output, timestamp } = node;

  const getIcon = () => {
    if (event_type === 'reasoning') return <Brain className="w-5 h-5 text-blue-400" />;
    if (event_type === 'search_result') return <Search className="w-5 h-5 text-green-400" />;
    if (event_type === 'summary') return <FileText className="w-5 h-5 text-purple-400" />;
    return <Activity className="w-5 h-5 text-gray-400" />;
  };

  const renderContent = (content) => {
    try {
      if (typeof content === 'string') {
        return <ReactMarkdown className="prose prose-invert prose-sm max-w-none">{content}</ReactMarkdown>;
      }
      if (Array.isArray(content)) {
        return (
          <div className="space-y-4">
            {content.map((item, i) => (
              <div key={i} className="bg-background p-3 rounded border border-gray-800">
                {item.content && (
                  <div className="mb-2">
                    <ReactMarkdown className="prose prose-invert prose-sm max-w-none">{item.content}</ReactMarkdown>
                  </div>
                )}
                {item.citations && item.citations.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {item.citations.map((url, j) => (
                      <button
                        key={j}
                        onClick={() => onOpenUrl(url)}
                        className="flex items-center gap-1 text-xs bg-primary/20 text-primary px-2 py-1 rounded hover:bg-primary/30 transition-colors"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Source {j + 1}
                      </button>
                    ))}
                  </div>
                )}
                {!item.content && !item.citations && <pre className="text-xs overflow-x-auto">{JSON.stringify(item, null, 2)}</pre>}
              </div>
            ))}
          </div>
        );
      }
      return <pre className="text-xs overflow-x-auto bg-background p-2 rounded">{JSON.stringify(content, null, 2)}</pre>;
    } catch (error) {
      return <pre className="text-xs overflow-x-auto bg-red-900/20 p-2 rounded text-red-400">Error rendering content: {error.message}</pre>;
    }
  };

  return (
    <div className="w-96 border-l border-gray-800 bg-surface flex flex-col h-full shadow-xl fixed right-0 top-0 z-50">
      <div className="p-4 border-b border-gray-800 flex items-center justify-between bg-surface">
        <div className="flex items-center gap-2 font-semibold">
          {getIcon()}
          <span>{source}</span>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Event Type</h4>
          <div className="text-sm bg-background px-3 py-1 rounded inline-block border border-gray-800">
            {event_type}
          </div>
        </div>

        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Timestamp</h4>
          <div className="text-sm text-gray-400 font-mono">
            {new Date(timestamp).toLocaleString()}
          </div>
        </div>

        {input && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Input</h4>
            <div className="bg-background rounded p-3 border border-gray-800 text-sm">
              {renderContent(input)}
            </div>
          </div>
        )}

        {output && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Output</h4>
            <div className="bg-background rounded p-3 border border-gray-800 text-sm">
              {renderContent(output)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
