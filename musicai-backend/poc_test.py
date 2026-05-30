"""
Proof of Concept Test Script

This script tests the complete pipeline:
1. User prompt → Ollama (enhancement)
2. Enhanced prompt → MusicGen (audio generation)
3. Audio → basic-pitch (MIDI conversion)
4. MIDI → music21 (Stream object)
5. music21 → Analysis + Exports (MusicXML, ABC)

Run this to validate all services are working correctly.
"""

import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.infrastructure.ai import (
    Music21Service,
    MusicGenService,
    AudioToMidiService,
    OllamaService
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_poc():
    """Run the proof of concept test."""

    logger.info("=" * 80)
    logger.info("MusicAI - Proof of Concept Test")
    logger.info("=" * 80)

    # Create output directory
    output_dir = Path("./poc_output")
    output_dir.mkdir(exist_ok=True)
    logger.info(f"Output directory: {output_dir.absolute()}")

    try:
        # ==================== Step 1: Initialize Services ====================
        logger.info("\n[STEP 1] Initializing services...")

        music21_svc = Music21Service()
        logger.info("✓ Music21 service ready")

        audio_to_midi_svc = AudioToMidiService()
        logger.info("✓ Audio-to-MIDI service ready")

        ollama_svc = OllamaService()
        logger.info("✓ Ollama service ready")

        logger.info("Loading MusicGen model (this may take a minute)...")
        musicgen_svc = MusicGenService(
            model_name="facebook/musicgen-small",  # Using small model for faster POC
            use_gpu=True
        )
        logger.info("✓ MusicGen service ready")

        # ==================== Step 2: Enhance Prompt ====================
        logger.info("\n[STEP 2] Enhancing user prompt with Ollama...")

        user_prompt = "A calm piano melody in C major"
        logger.info(f"User prompt: '{user_prompt}'")

        enhanced = ollama_svc.enhance_music_prompt(user_prompt)
        logger.info(f"Enhanced prompt: '{enhanced['enhanced_prompt']}'")
        logger.info(f"Extracted params: {enhanced}")

        # ==================== Step 3: Generate Audio ====================
        logger.info("\n[STEP 3] Generating audio with MusicGen...")

        audio_array, sample_rate = musicgen_svc.generate_from_text(
            prompt=enhanced['enhanced_prompt'],
            duration=10  # Short duration for POC
        )
        logger.info(f"Generated audio: {len(audio_array) / sample_rate:.2f}s at {sample_rate} Hz")

        # Save audio
        audio_path = output_dir / "generated_audio.wav"
        musicgen_svc.save_audio(audio_array, str(audio_path), sample_rate)
        logger.info(f"✓ Saved audio: {audio_path}")

        # ==================== Step 4: Convert Audio to MIDI ====================
        logger.info("\n[STEP 4] Converting audio to MIDI with basic-pitch...")

        midi_bytes = audio_to_midi_svc.convert_audio_to_midi(
            str(audio_path),
            onset_threshold=0.5,
            frame_threshold=0.3
        )
        logger.info(f"Converted to MIDI: {len(midi_bytes)} bytes")

        # Save MIDI
        midi_path = output_dir / "converted.mid"
        with open(midi_path, 'wb') as f:
            f.write(midi_bytes)
        logger.info(f"✓ Saved MIDI: {midi_path}")

        # Analyze MIDI quality
        quality = audio_to_midi_svc.analyze_midi_quality(midi_bytes)
        logger.info(f"MIDI quality: {quality}")

        # ==================== Step 5: Load into music21 ====================
        logger.info("\n[STEP 5] Loading MIDI into music21 Stream...")

        stream_obj = music21_svc.from_midi_bytes(midi_bytes)
        logger.info(f"✓ Created music21 Stream object")
        logger.info(f"Stream type: {type(stream_obj)}")

        # ==================== Step 6: Analyze with music21 ====================
        logger.info("\n[STEP 6] Analyzing music with music21...")

        analysis = music21_svc.analyze(stream_obj)
        logger.info("Analysis results:")
        for key, value in analysis.items():
            logger.info(f"  {key}: {value}")

        # ==================== Step 7: Export to Multiple Formats ====================
        logger.info("\n[STEP 7] Exporting to multiple formats...")

        # Export MusicXML
        musicxml_str = music21_svc.to_musicxml(stream_obj)
        musicxml_path = output_dir / "piece.musicxml"
        with open(musicxml_path, 'w') as f:
            f.write(musicxml_str)
        logger.info(f"✓ Saved MusicXML: {musicxml_path}")

        # Export ABC
        try:
            abc_str = music21_svc.to_abc(stream_obj)
            abc_path = output_dir / "piece.abc"
            with open(abc_path, 'w') as f:
                f.write(abc_str)
            logger.info(f"✓ Saved ABC: {abc_path}")
        except Exception as e:
            logger.warning(f"Could not export ABC: {e}")

        # Serialize to JSON
        json_str = music21_svc.to_json(stream_obj)
        json_path = output_dir / "stream.json"
        with open(json_path, 'w') as f:
            f.write(json_str)
        logger.info(f"✓ Saved music21 JSON: {json_path}")

        # ==================== Step 8: Test Transformations ====================
        logger.info("\n[STEP 8] Testing transformations...")

        # Transpose
        transposed = music21_svc.transpose(stream_obj, 2)  # Up 2 semitones
        transposed_midi_path = output_dir / "transposed.mid"
        with open(transposed_midi_path, 'wb') as f:
            f.write(music21_svc.to_midi_bytes(transposed))
        logger.info(f"✓ Transposed +2 semitones: {transposed_midi_path}")

        # Retrograde
        retrograde = music21_svc.retrograde(stream_obj)
        retrograde_midi_path = output_dir / "retrograde.mid"
        with open(retrograde_midi_path, 'wb') as f:
            f.write(music21_svc.to_midi_bytes(retrograde))
        logger.info(f"✓ Created retrograde: {retrograde_midi_path}")

        # ==================== Step 9: Explain with Ollama ====================
        logger.info("\n[STEP 9] Getting natural language explanation...")

        explanation = ollama_svc.explain_analysis(analysis)
        logger.info("Explanation:")
        logger.info(explanation)

        # ==================== Summary ====================
        logger.info("\n" + "=" * 80)
        logger.info("✅ PROOF OF CONCEPT COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"\nGenerated files in: {output_dir.absolute()}")
        logger.info("  - generated_audio.wav (original audio)")
        logger.info("  - converted.mid (MIDI from audio)")
        logger.info("  - piece.musicxml (notation)")
        logger.info("  - stream.json (music21 serialization)")
        logger.info("  - transposed.mid (transformation example)")
        logger.info("  - retrograde.mid (transformation example)")
        logger.info("\n🎵 Pipeline: Prompt → Audio → MIDI → music21 → Exports ✓")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ Error during POC: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_poc()
