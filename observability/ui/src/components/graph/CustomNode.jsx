import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { Search, FileText, Eye, Bot, Brain, CheckCircle } from 'lucide-react';

const CustomNode = ({ data, selected }) => {
    const getIcon = () => {
        switch (data.type) {
            case 'search_result': return <Search className="w-4 h-4 text-green-400" />;
            case 'reasoning': return <Brain className="w-4 h-4 text-blue-400" />;
            case 'analysis': return <FileText className="w-4 h-4 text-purple-400" />;
            case 'review': return <Eye className="w-4 h-4 text-orange-400" />;
            case 'prediction': return <Bot className="w-4 h-4 text-pink-400" />;
            case 'summary': return <CheckCircle className="w-4 h-4 text-cyan-400" />;
            default: return <Bot className="w-4 h-4 text-gray-400" />;
        }
    };

    const getColors = () => {
        switch (data.type) {
            case 'search_result': return 'border-green-500/50 bg-green-500/10';
            case 'reasoning': return 'border-blue-500/50 bg-blue-500/10';
            case 'analysis': return 'border-purple-500/50 bg-purple-500/10';
            case 'review': return 'border-orange-500/50 bg-orange-500/10';
            case 'prediction': return 'border-pink-500/50 bg-pink-500/10';
            case 'summary': return 'border-cyan-500/50 bg-cyan-500/10';
            default: return 'border-gray-500/50 bg-gray-500/10';
        }
    };

    return (
        <div className={`
      px-4 py-2 rounded-lg border shadow-lg min-w-[150px]
      flex items-center gap-3 transition-all duration-200
      ${getColors()}
      ${selected ? 'ring-2 ring-white/50 scale-105' : ''}
      ${data.isOrphan ? 'ring-2 ring-red-500 bg-red-500/20' : ''}
    `}>
            <Handle type="target" position={Position.Top} className="!bg-[var(--text-muted)]" />

            <div className="p-1.5 rounded-full bg-black/20">
                {getIcon()}
            </div>

            <div className="flex flex-col">
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                    {data.label}
                </span>
                <span className="text-[10px] text-[var(--text-muted)] capitalize">
                    {data.source.replace('Agent', '')}
                </span>
            </div>

            <Handle type="source" position={Position.Bottom} className="!bg-[var(--text-muted)]" />
        </div>
    );
};

export default memo(CustomNode);
