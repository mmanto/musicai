/**
 * MusicAwareText Component
 *
 * Parses text containing [music type="..."]...[/music] tags
 * and renders inline musical notation using InlineNotation component.
 */

import React from 'react';
import InlineNotation from './InlineNotation';

interface MusicAwareTextProps {
  text: string;
  className?: string;
}

type MusicType = 'scale' | 'chord' | 'notes' | 'interval' | 'progression';

interface ParsedPart {
  type: 'text' | 'music';
  content: string;
  musicType?: MusicType;
}

function parseMusicTags(text: string): ParsedPart[] {
  const parts: ParsedPart[] = [];

  // Regex to match [music type="..."]...[/music]
  const musicTagRegex = /\[music\s+type="(scale|chord|notes|interval|progression)"\](.*?)\[\/music\]/gi;

  let lastIndex = 0;
  let match;

  while ((match = musicTagRegex.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      const textBefore = text.substring(lastIndex, match.index);
      if (textBefore) {
        parts.push({ type: 'text', content: textBefore });
      }
    }

    // Add the music notation
    const musicType = match[1].toLowerCase() as MusicType;
    const musicContent = match[2].trim();

    parts.push({
      type: 'music',
      content: musicContent,
      musicType,
    });

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after last match
  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.substring(lastIndex) });
  }

  // If no matches found, return the whole text
  if (parts.length === 0) {
    parts.push({ type: 'text', content: text });
  }

  return parts;
}

export default function MusicAwareText({ text, className }: MusicAwareTextProps) {
  // Handle null/undefined/empty text
  if (!text) {
    return <span className={`music-aware-text ${className || ''}`}></span>;
  }

  const parts = parseMusicTags(text);

  return (
    <span className={`music-aware-text ${className || ''}`}>
      {parts.map((part, index) => {
        if (part.type === 'text') {
          // Render text, preserving line breaks
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
        } else {
          // Render inline notation
          return (
            <InlineNotation
              key={index}
              type={part.musicType!}
              content={part.content}
            />
          );
        }
      })}
    </span>
  );
}
