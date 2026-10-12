import React, { useState } from 'react';
import { Copy, Check, Download } from 'lucide-react';
import katex from 'katex';

function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3.5 rounded-xl overflow-hidden border border-slate-700/60 bg-slate-900/95 shadow-md">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-800/80 border-b border-slate-700/50 text-xs text-slate-400 font-mono">
        <span className="uppercase font-semibold tracking-wider text-slate-300">
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-0.5 rounded text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
          title="Copy code"
        >
          {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre className="p-3.5 overflow-x-auto text-xs font-mono text-slate-200 leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function MathDisplayBlock({ math }) {
  try {
    const html = katex.renderToString(math.trim(), {
      displayMode: true,
      throwOnError: false,
    });
    return (
      <div
        className="my-3.5 py-3 px-4 overflow-x-auto rounded-2xl bg-purple-50/70 dark:bg-purple-950/30 border border-purple-200/80 dark:border-purple-500/30 text-center shadow-xs text-slate-900 dark:text-slate-100 transition-colors"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  } catch (e) {
    return (
      <pre className="my-2 p-2.5 bg-slate-900 text-rose-400 font-mono text-xs rounded-xl overflow-x-auto">
        {math}
      </pre>
    );
  }
}

function renderInlineMath(text) {
  try {
    const html = katex.renderToString(text.trim(), {
      displayMode: false,
      throwOnError: false,
    });
    return (
      <span
        className="inline-katex inline-block px-0.5 align-baseline text-slate-900 dark:text-slate-100"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  } catch (e) {
    return <code className="text-purple-600 dark:text-purple-300 font-mono text-xs">{text}</code>;
  }
}

export function MarkdownContent({ content }) {
  if (!content) return null;

  // Split into code blocks, math display blocks ($$...$$, \[...\], \begin{...}...\end{...}), and normal text
  const parts = [];
  const blockRegex = /(```([^\n]*)\n([\s\S]*?)```|\$\$([\s\S]*?)\$\$|\\\[([\s\S]*?)\\\]|(\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?|matrix|pmatrix|bmatrix|vmatrix|Vmatrix|cases)\}[\s\S]*?\\end\{(?:equation\*?|align\*?|gather\*?|multline\*?|matrix|pmatrix|bmatrix|vmatrix|Vmatrix|cases)\}))/g;
  let lastIndex = 0;
  let match;

  while ((match = blockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.substring(lastIndex, match.index),
      });
    }

    if (match[1]?.startsWith('```')) {
      // Code block
      parts.push({
        type: 'code',
        language: match[2]?.trim() || 'text',
        code: match[3],
      });
    } else if (match[4] || match[5] || match[6]) {
      // Display Math block ($$...$$ or \[...\] or \begin{...}...\end{...})
      parts.push({
        type: 'math',
        math: (match[4] || match[5] || match[6]).trim(),
      });
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      content: content.substring(lastIndex),
    });
  }

  // Parse markdown tables and text lines
  const renderTextSegment = (text, segKey) => {
    const lines = text.split('\n');
    const nodes = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Check for table header: | a | b |
      if (line.trim().startsWith('|') && line.trim().endsWith('|') && i + 1 < lines.length && lines[i + 1].includes('|-')) {
        const tableLines = [line];
        i++; // separator
        i++;
        while (i < lines.length && lines[i].trim().startsWith('|')) {
          tableLines.push(lines[i]);
          i++;
        }

        // Render Table
        const headers = tableLines[0].split('|').map((c) => c.trim()).filter(Boolean);
        const rows = tableLines.slice(1).map((tl) =>
          tl.split('|').map((c) => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
        );

        nodes.push(
          <div key={`table-${segKey}-${i}`} className="my-3 overflow-x-auto rounded-xl border border-slate-700/60 shadow-md">
            <table className="w-full text-left text-xs text-slate-200">
              <thead className="bg-slate-800/90 text-slate-100 uppercase tracking-wider font-semibold border-b border-slate-700/60">
                <tr>
                  {headers.map((h, hIdx) => (
                    <th key={hIdx} className="px-3.5 py-2">
                      {renderInlineFormatting(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 bg-slate-900/60">
                {rows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3.5 py-2">
                        {renderInlineFormatting(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }

      // Check for horizontal divider: ---, ***, ___
      if (/^(\s*[-*_]\s*){3,}$/.test(line)) {
        nodes.push(
          <hr key={`hr-${segKey}-${i}`} className="my-3.5 border-t border-slate-300/80 dark:border-slate-700/70" />
        );
        i++;
        continue;
      }

      // Headers
      if (line.startsWith('#### ')) {
        nodes.push(
          <h4 key={`h4-${segKey}-${i}`} className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-2.5 mb-1">
            {renderInlineFormatting(line.slice(5))}
          </h4>
        );
      } else if (line.startsWith('### ')) {
        nodes.push(
          <h3 key={`h3-${segKey}-${i}`} className="text-base font-semibold text-slate-900 dark:text-slate-100 mt-3 mb-1">
            {renderInlineFormatting(line.slice(4))}
          </h3>
        );
      } else if (line.startsWith('## ')) {
        nodes.push(
          <h2 key={`h2-${segKey}-${i}`} className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-4 mb-2">
            {renderInlineFormatting(line.slice(3))}
          </h2>
        );
      } else if (line.startsWith('# ')) {
        nodes.push(
          <h1 key={`h1-${segKey}-${i}`} className="text-xl font-extrabold text-slate-950 dark:text-slate-50 mt-4 mb-2">
            {renderInlineFormatting(line.slice(2))}
          </h1>
        );
      } else if (line.startsWith('> ')) {
        nodes.push(
          <blockquote key={`bq-${segKey}-${i}`} className="border-l-2 border-brand-500 pl-3 py-1 text-slate-600 dark:text-slate-400 italic my-2">
            {renderInlineFormatting(line.slice(2))}
          </blockquote>
        );
      } else if (line.startsWith('- ') || line.startsWith('* ') || line.startsWith('+ ')) {
        nodes.push(
          <li key={`li-${segKey}-${i}`} className="ml-4 list-disc text-slate-800 dark:text-slate-200">
            {renderInlineFormatting(line.slice(2))}
          </li>
        );
      } else if (/^\d+\.\s/.test(line)) {
        const numPart = line.match(/^\d+\.\s/)[0];
        nodes.push(
          <li key={`oli-${segKey}-${i}`} className="ml-4 list-decimal text-slate-800 dark:text-slate-200">
            {renderInlineFormatting(line.slice(numPart.length))}
          </li>
        );
      } else if (!line.trim()) {
        nodes.push(<div key={`sp-${segKey}-${i}`} className="h-2" />);
      } else {
        nodes.push(
          <p key={`p-${segKey}-${i}`} className="my-1.5 leading-relaxed text-slate-800 dark:text-slate-200">
            {renderInlineFormatting(line)}
          </p>
        );
      }
      i++;
    }

    return (
      <div key={segKey} className="space-y-1.5 text-sm leading-relaxed">
        {nodes}
      </div>
    );
  };

  // Inline formatting: LaTeX ($math$), Images, Links, Bold, Italic, Inline Code
  const renderInlineFormatting = (str) => {
    const API_HOST = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://localhost:8000'
      : '';

    // Check for Images first: ![alt](url)
    const imgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
    const elements = [];
    let lastIdx = 0;
    let m;

    while ((m = imgRegex.exec(str)) !== null) {
      if (m.index > lastIdx) {
        elements.push(renderMathAndLinks(str.substring(lastIdx, m.index), `sub-${lastIdx}`));
      }
      const alt = m[1];
      const rawUrl = m[2];
      const fullUrl = rawUrl.startsWith('/') ? `${API_HOST}${rawUrl}` : rawUrl;

      elements.push(
        <div key={`img-${m.index}`} className="my-3 rounded-2xl overflow-hidden border border-slate-700/80 bg-slate-900 shadow-xl max-w-lg">
          <div className="relative group/img bg-slate-950 flex items-center justify-center overflow-hidden">
            <img
              src={fullUrl}
              alt={alt}
              loading="lazy"
              className="w-full h-auto max-h-[420px] object-cover transition-transform duration-300 group-hover/img:scale-[1.01]"
            />
          </div>
          <div className="p-3 bg-slate-850 border-t border-slate-700/60 flex items-center justify-between text-xs text-slate-300">
            <span className="truncate max-w-[260px] font-medium text-slate-200">
              {alt || 'AI Generated Image'}
            </span>
            <a
              href={fullUrl}
              download
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-medium transition-colors shadow-sm"
            >
              <Download size={13} />
              <span>Download</span>
            </a>
          </div>
        </div>
      );
      lastIdx = m.index + m[0].length;
    }

    if (lastIdx < str.length) {
      elements.push(renderMathAndLinks(str.substring(lastIdx), `sub-${lastIdx}`));
    }

    return elements;
  };

  const renderMathAndLinks = (str, keyPrefix) => {
    // Check for inline / display math: \(...\) or \[...\] or $...$
    const mathRegex = /(?:\\\(([\s\S]*?)\\\)|\\\[([\s\S]*?)\\\]|\$([^\$\n\s](?:[^\$\n]*?[^\$\n\s])?)\$)/g;
    const items = [];
    let cur = 0;
    let match;

    while ((match = mathRegex.exec(str)) !== null) {
      if (match.index > cur) {
        items.push(renderLinksAndStyles(str.substring(cur, match.index), `${keyPrefix}-m-${cur}`));
      }
      const mathExpr = match[1] || match[2] || match[3];
      const isDisplay = Boolean(match[2]);
      items.push(
        <span
          key={`${keyPrefix}-math-${match.index}`}
          className={
            isDisplay
              ? 'my-2 block text-center'
              : 'mx-0.5 inline-block align-baseline text-slate-900 dark:text-slate-100 font-sans'
          }
        >
          {isDisplay ? <MathDisplayBlock math={mathExpr} /> : renderInlineMath(mathExpr)}
        </span>
      );
      cur = match.index + match[0].length;
    }

    if (cur < str.length) {
      items.push(renderLinksAndStyles(str.substring(cur), `${keyPrefix}-m-${cur}`));
    }

    return items;
  };

  const renderLinksAndStyles = (str, keyPrefix) => {
    // Links: [text](url)
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    const elements = [];
    let lastIdx = 0;
    let m;

    while ((m = linkRegex.exec(str)) !== null) {
      if (m.index > lastIdx) {
        elements.push(formatStyles(str.substring(lastIdx, m.index), `${keyPrefix}-l-${lastIdx}`));
      }
      elements.push(
        <a
          key={`${keyPrefix}-link-${m.index}`}
          href={m[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-400 hover:text-brand-300 underline font-medium inline-flex items-center gap-0.5"
        >
          {m[1]}
        </a>
      );
      lastIdx = m.index + m[0].length;
    }

    if (lastIdx < str.length) {
      elements.push(formatStyles(str.substring(lastIdx), `${keyPrefix}-l-${lastIdx}`));
    }

    return elements;
  };

  const formatStyles = (subStr, key) => {
    // Inline code: `code`
    const parts = subStr.split(/(`[^`]+`)/);
    return (
      <span key={key}>
        {parts.map((p, pIdx) => {
          if (p.startsWith('`') && p.endsWith('`')) {
            return (
              <code
                key={pIdx}
                className="px-1.5 py-0.5 mx-0.5 bg-slate-200 dark:bg-slate-800 text-purple-700 dark:text-brand-300 rounded font-mono text-xs border border-purple-200/60 dark:border-slate-700/50"
              >
                {p.slice(1, -1)}
              </code>
            );
          }

          // Bold: **text**
          const boldParts = p.split(/(\*\*[^*]+\*\*)/);
          return boldParts.map((b, bIdx) => {
            if (b.startsWith('**') && b.endsWith('**')) {
              return (
                <strong key={bIdx} className="font-semibold text-slate-900 dark:text-slate-100">
                  {b.slice(2, -2)}
                </strong>
              );
            }
            return b;
          });
        })}
      </span>
    );
  };

  return (
    <div className="space-y-2">
      {parts.map((part, idx) => {
        if (part.type === 'code') {
          return <CodeBlock key={idx} language={part.language} code={part.code} />;
        }
        if (part.type === 'math') {
          return <MathDisplayBlock key={idx} math={part.math} />;
        }
        return renderTextSegment(part.content, idx);
      })}
    </div>
  );
}
