import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';
import InlineNotation from './InlineNotation';

interface MusicAwareTextProps {
  text: string;
  className?: string;
  markdown?: boolean;
}

type MusicType = 'scale' | 'chord' | 'notes' | 'interval' | 'progression';

interface ParsedPart {
  type: 'text' | 'music';
  content: string;
  musicType?: MusicType;
}

function parseMusicTags(text: string): ParsedPart[] {
  const parts: ParsedPart[] = [];
  const musicTagRegex = /\[music\s+type="(scale|chord|notes|interval|progression)"\](.*?)\[\/music\]/gi;
  let lastIndex = 0;
  let match;

  while ((match = musicTagRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      const textBefore = text.substring(lastIndex, match.index);
      if (textBefore) parts.push({ type: 'text', content: textBefore });
    }
    parts.push({
      type: 'music',
      content: match[2].trim(),
      musicType: match[1].toLowerCase() as MusicType,
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.substring(lastIndex) });
  }

  if (parts.length === 0) {
    parts.push({ type: 'text', content: text });
  }

  return parts;
}

// Tailwind classes applied to each markdown element
const mdComponents: Components = {
  h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2 text-foreground">{children}</h1>,
  h2: ({ children }) => <h2 className="text-lg font-semibold mt-3 mb-1.5 text-foreground">{children}</h2>,
  h3: ({ children }) => <h3 className="text-base font-semibold mt-2 mb-1 text-foreground">{children}</h3>,
  p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5 pl-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5 pl-1">{children}</ol>,
  li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  code: ({ children, className }) => {
    const isBlock = className?.includes('language-');
    if (isBlock) {
      return (
        <code className="block bg-muted text-muted-foreground rounded-md px-3 py-2 text-xs font-mono overflow-x-auto my-2">
          {children}
        </code>
      );
    }
    return (
      <code className="bg-muted text-muted-foreground rounded px-1 py-0.5 text-xs font-mono">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <pre className="my-2 overflow-x-auto">{children}</pre>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-border pl-3 text-muted-foreground italic my-2">
      {children}
    </blockquote>
  ),
  a: ({ href, children }) => (
    <a href={href} className="text-primary underline underline-offset-2 hover:text-primary/80" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  hr: () => <hr className="border-border my-3" />,
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="text-xs border-collapse w-full">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border border-border px-2 py-1 bg-muted font-medium text-left">{children}</th>,
  td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
};

export default function MusicAwareText({ text, className, markdown = false }: MusicAwareTextProps) {
  if (!text) {
    return <span className={`music-aware-text ${className || ''}`}></span>;
  }

  const parts = parseMusicTags(text);

  // Plain text mode (user messages, system messages)
  if (!markdown) {
    return (
      <span className={`music-aware-text ${className || ''}`}>
        {parts.map((part, index) => {
          if (part.type === 'text') {
            return (
              <React.Fragment key={index}>
                {part.content.split('\n').map((line, lineIndex, arr) => (
                  <React.Fragment key={lineIndex}>
                    {line}
                    {lineIndex < arr.length - 1 && <br />}
                  </React.Fragment>
                ))}
              </React.Fragment>
            );
          }
          return <InlineNotation key={index} type={part.musicType!} content={part.content} />;
        })}
      </span>
    );
  }

  // Markdown mode (assistant messages)
  return (
    <div className={`music-aware-text text-sm text-foreground ${className || ''}`}>
      {parts.map((part, index) => {
        if (part.type === 'text') {
          return (
            <ReactMarkdown key={index} remarkPlugins={[remarkGfm]} components={mdComponents}>
              {part.content}
            </ReactMarkdown>
          );
        }
        return <InlineNotation key={index} type={part.musicType!} content={part.content} />;
      })}
    </div>
  );
}
