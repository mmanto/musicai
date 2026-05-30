from app.infrastructure.ai.music21_service import Music21Service

# Test scale generation
service = Music21Service()
scale_stream = service.create_scale(tonic='C', scale_type='major', octaves=1)

# Convert to MusicXML
musicxml = service.to_musicxml(scale_stream)
print("MusicXML length:", len(musicxml))
print("\n=== MusicXML Content ===")
print(musicxml)

# Count notes
notes = scale_stream.flatten().notes
print(f"\n=== Note count: {len(notes)} ===")
for i, n in enumerate(notes, 1):
    print(f"{i}. {n.nameWithOctave} - duration: {n.quarterLength}")
