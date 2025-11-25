import React from 'react';
import { detectCardType } from '../../utils/cardHelpers';
import TextCard from './TextCard';
import CodeCard from './CodeCard';
import ArrayCard from './ArrayCard';
import ObjectCard from './ObjectCard';

const JsonCard = ({ label, value, nested = false }) => {
    const type = detectCardType(label, value);

    // Handle null/undefined
    if (type === 'null') {
        return (
            <div className="text-xs text-[var(--text-muted)] italic">
                {label}: null
            </div>
        );
    }

    // Handle primitives
    if (type === 'primitive') {
        return (
            <div className="mb-2">
                <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                    {label}:
                </span>
                <span className="ml-2 text-sm text-[var(--text-secondary)]">
                    {String(value)}
                </span>
            </div>
        );
    }

    // Handle text
    if (type === 'text') {
        return <TextCard label={label} value={value} />;
    }

    // Handle code
    if (type === 'code') {
        return <CodeCard label={label} value={value} />;
    }

    // Handle arrays
    if (type === 'array') {
        return <ArrayCard label={label} value={value} />;
    }

    // Handle objects
    if (type === 'object') {
        return <ObjectCard label={label} value={value} nested={nested} />;
    }

    // Fallback
    return (
        <div className="text-xs text-red-400">
            Unknown type for {label}
        </div>
    );
};

export default JsonCard;
