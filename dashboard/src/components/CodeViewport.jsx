import React from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const customStyle = {
  ...vscDarkPlus,
  'pre[class*="language-"]': {
    ...vscDarkPlus['pre[class*="language-"]'],
    background: '#1a1a2e',
    margin: 0,
    padding: '12px',
    fontSize: '11px',
    lineHeight: '1.6',
  },
  'code[class*="language-"]': {
    ...vscDarkPlus['code[class*="language-"]'],
    background: 'transparent',
    fontSize: '11px',
    lineHeight: '1.6',
  },
};

export default function CodeViewport({ code }) {
  if (!code) {
    return (
      <div className="code-viewport p-4 text-gray-500 text-xs">
        Awaiting target...
      </div>
    );
  }

  return (
    <div className="code-viewport overflow-auto max-h-[300px]">
      <SyntaxHighlighter
        language="javascript"
        style={customStyle}
        showLineNumbers
        lineNumberStyle={{
          color: '#444',
          fontSize: '11px',
          paddingRight: '12px',
          borderRight: '1px solid #2a2a3e',
          minWidth: '30px',
          textAlign: 'right',
          userSelect: 'none',
        }}
        wrapLines
        customStyle={{
          background: '#1a1a2e',
          borderRadius: '6px',
          margin: 0,
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
