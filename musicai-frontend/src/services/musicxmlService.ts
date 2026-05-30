/**
 * MusicXML Service
 *
 * Utilities for parsing and manipulating MusicXML files
 * Converts between MusicXML and VexFlow note format
 */

export interface VexFlowNote {
  keys: string[];
  duration: string;
  accidental?: string;
}

/**
 * Parses MusicXML content and extracts notes in VexFlow format
 * This is a basic implementation that handles simple monophonic melodies
 */
export async function parseMusicXMLToVexFlow(musicxmlUrl: string): Promise<VexFlowNote[]> {
  try {
    console.log('🎵 Parsing MusicXML from:', musicxmlUrl);

    // Fetch the MusicXML file
    const response = await fetch(musicxmlUrl);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const xmlText = await response.text();
    console.log('📄 XML Text length:', xmlText.length);

    // Parse XML
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, 'text/xml');

    // Check for parsing errors
    const parserError = xmlDoc.querySelector('parsererror');
    if (parserError) {
      console.error('❌ XML Parser error:', parserError.textContent);
      throw new Error('Failed to parse MusicXML');
    }

    const notes: VexFlowNote[] = [];

    // Get all note elements from all parts and measures
    const noteElements = xmlDoc.querySelectorAll('note');
    console.log('🎼 Found note elements:', noteElements.length);

    noteElements.forEach((noteElement, index) => {
      // Skip rest notes
      const rest = noteElement.querySelector('rest');
      if (rest) {
        console.log(`  Note ${index + 1}: REST - skipping`);
        return;
      }

      // Get pitch information
      const pitch = noteElement.querySelector('pitch');
      if (!pitch) {
        console.log(`  Note ${index + 1}: No pitch element - skipping`);
        return;
      }

      const step = pitch.querySelector('step')?.textContent || 'C';
      const octave = pitch.querySelector('octave')?.textContent || '4';
      const alter = pitch.querySelector('alter')?.textContent;

      // Get duration information
      const typeElement = noteElement.querySelector('type');
      if (!typeElement) {
        console.log(`  Note ${index + 1}: No type element - skipping`);
        return;
      }

      const noteType = typeElement.textContent || 'quarter';

      // Map MusicXML note types to VexFlow durations
      const durationMap: { [key: string]: string } = {
        'whole': 'w',
        'half': 'h',
        'quarter': 'q',
        'eighth': '8',
        '16th': '16',
        '32nd': '32',
      };

      const vexDuration = durationMap[noteType] || 'q';

      // Build VexFlow key (e.g., "c/4", "d#/5")
      let key = step.toLowerCase() + '/' + octave;

      // Handle accidentals
      let accidental: string | undefined;
      if (alter) {
        const alterValue = parseInt(alter);
        if (alterValue > 0) {
          accidental = '#';
          key += '#';
        } else if (alterValue < 0) {
          accidental = 'b';
          key += 'b';
        }
      }

      const note: VexFlowNote = {
        keys: [key],
        duration: vexDuration,
      };

      if (accidental) {
        note.accidental = accidental;
      }

      console.log(`  Note ${index + 1}: ${key} (${vexDuration}) ${accidental || ''}`);
      notes.push(note);
    });

    console.log('✅ Successfully parsed notes:', notes.length);

    // If no notes were parsed, return default notes
    if (notes.length === 0) {
      console.warn('⚠️ No notes found, returning defaults');
      return [
        { keys: ['c/4'], duration: 'q' },
        { keys: ['d/4'], duration: 'q' },
        { keys: ['e/4'], duration: 'q' },
        { keys: ['f/4'], duration: 'q' },
      ];
    }

    return notes;
  } catch (error) {
    console.error('❌ Error parsing MusicXML:', error);
    // Return default notes on error
    return [
      { keys: ['c/4'], duration: 'q' },
      { keys: ['d/4'], duration: 'q' },
      { keys: ['e/4'], duration: 'q' },
      { keys: ['f/4'], duration: 'q' },
    ];
  }
}

/**
 * Converts VexFlow notes to a basic MusicXML string
 * This generates a simple monophonic score
 */
export function vexFlowNotesToMusicXML(notes: VexFlowNote[]): string {
  // Map VexFlow durations to MusicXML types and divisions
  const durationMap: { [key: string]: { type: string; duration: number } } = {
    'w': { type: 'whole', duration: 4 },
    'h': { type: 'half', duration: 2 },
    'q': { type: 'quarter', duration: 1 },
    '8': { type: 'eighth', duration: 0.5 },
    '16': { type: '16th', duration: 0.25 },
  };

  let xml = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1">
      <part-name>Piano</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key>
          <fifths>0</fifths>
        </key>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
        <clef>
          <sign>G</sign>
          <line>2</line>
        </clef>
      </attributes>
`;

  // Add each note
  notes.forEach((note) => {
    const durationInfo = durationMap[note.duration] || { type: 'quarter', duration: 1 };

    // Parse the key (e.g., "c/4" or "d#/5")
    const [pitchStr, octave] = note.keys[0].split('/');
    const step = pitchStr[0].toUpperCase();

    // Handle accidentals
    let alter = 0;
    if (note.accidental === '#') {
      alter = 1;
    } else if (note.accidental === 'b') {
      alter = -1;
    }

    xml += `      <note>
        <pitch>
          <step>${step}</step>
`;

    if (alter !== 0) {
      xml += `          <alter>${alter}</alter>
`;
    }

    xml += `          <octave>${octave}</octave>
        </pitch>
        <duration>${durationInfo.duration}</duration>
        <type>${durationInfo.type}</type>
      </note>
`;
  });

  xml += `    </measure>
  </part>
</score-partwise>`;

  return xml;
}

/**
 * Saves edited notes back to the backend
 */
export async function saveEditedScore(
  pieceId: string,
  notes: VexFlowNote[]
): Promise<{ success: boolean; musicxml_url?: string; error?: string }> {
  try {
    // Convert notes to MusicXML
    const musicxmlContent = vexFlowNotesToMusicXML(notes);

    // Create a Blob and FormData
    const blob = new Blob([musicxmlContent], { type: 'application/xml' });
    const formData = new FormData();
    formData.append('piece_id', pieceId);
    formData.append('musicxml_file', blob, 'edited.musicxml');

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const response = await fetch(`${baseUrl}/api/v1/music/update-score`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to save score');
    }

    const data = await response.json();
    return {
      success: true,
      musicxml_url: data.musicxml_url,
    };
  } catch (error: any) {
    console.error('Error saving edited score:', error);
    return {
      success: false,
      error: error.message || 'Unknown error',
    };
  }
}
