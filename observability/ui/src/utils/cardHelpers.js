// Detect card type based on content
export function detectCardType(key, value) {
    if (value === null || value === undefined) {
        return 'null';
    }

    if (typeof value === 'boolean' || typeof value === 'number') {
        return 'primitive';
    }

    if (typeof value === 'string') {
        // Check for code patterns
        const codePatterns = [
            /^def\s+\w+/m,           // Python function
            /^function\s+\w+/m,      // JavaScript function  
            /^import\s+/m,           // Import statement
            /^from\s+\w+\s+import/m, // Python import
            /^\s{2,}\w+/m,           // Indented code
            /=>/,                    // Arrow function
            /{\s*\n/,                // Opening brace with newline
        ];

        if (codePatterns.some(pattern => pattern.test(value))) {
            return 'code';
        }

        return 'text';
    }

    if (Array.isArray(value)) {
        return 'array';
    }

    if (typeof value === 'object') {
        return 'object';
    }

    return 'unknown';
}

// Detect language for code highlighting
export function detectLanguage(code) {
    if (/^def\s+\w+|import\s+\w+|from\s+\w+\s+import/.test(code)) {
        return 'python';
    }
    if (/^function\s+\w+|const\s+\w+|let\s+\w+|var\s+\w+|=>/.test(code)) {
        return 'javascript';
    }
    if (/^{\s*"/.test(code.trim())) {
        return 'json';
    }
    return 'python'; // default
}
