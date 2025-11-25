import React, { useState, useEffect } from 'react';
import { Copy, Check, Code2 } from 'lucide-react';
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import javascript from 'highlight.js/lib/languages/javascript';
import json from 'highlight.js/lib/languages/json';
import { detectLanguage } from '../../utils/cardHelpers';

// Register languages
hljs.registerLanguage('python', python);
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('json', json);

const CodeCard = ({ label, value }) => {
    const [copied, setCopied] = useState(false);
    const [highlightedCode, setHighlightedCode] = useState('');
    const language = detectLanguage(value);

    useEffect(() => {
        try {
            const result = hljs.highlight(value, { language });
            setHighlightedCode(result.value);
        } catch (error) {
            setHighlightedCode(value);
        }
    }, [value, language]);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="card p-4 mb-3">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-purple-400" />
                    <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                        {label}
                    </span>
                    <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 text-xs rounded">
                        {language}
                    </span>
                </div>
                <button
                    onClick={copyToClipboard}
                    className="p-1.5 hover:bg-[var(--bg-tertiary)] rounded transition-colors"
                    title="Copy code"
                >
                    {copied ? (
                        <Check className="w-4 h-4 text-green-400" />
                    ) : (
                        <Copy className="w-4 h-4 text-[var(--text-muted)]" />
                    )}
                </button>
            </div>
            <pre className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-md p-4 overflow-x-auto">
                <code
                    className={`hljs language-${language} text-sm`}
                    dangerouslySetInnerHTML={{ __html: highlightedCode }}
                />
            </pre>
        </div>
    );
};

export default CodeCard;
