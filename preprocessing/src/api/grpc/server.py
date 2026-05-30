"""gRPC server implementation for preprocessing service."""

import logging
from concurrent import futures
import uuid

import grpc

from ...config import get_settings
from ...tokenizer import BPETokenizer
from ...audio import AudioFeatureExtractor, SpectrogramGenerator, AudioToMidiConverter

logger = logging.getLogger(__name__)

# Note: Proto files need to be compiled first
# Run: python -m grpc_tools.protoc -I protos --python_out=src/api/grpc --grpc_python_out=src/api/grpc protos/preprocessing.proto


class PreprocessingServicer:
    """
    gRPC service implementation for preprocessing.

    This servicer implements the PreprocessingService defined in preprocessing.proto.
    """

    def __init__(self):
        """Initialize servicer with processing components."""
        self.tokenizer = BPETokenizer()
        self.feature_extractor = AudioFeatureExtractor()
        self.spectrogram_generator = SpectrogramGenerator()
        self.audio_to_midi = AudioToMidiConverter()

        settings = get_settings()
        self.service_name = settings.SERVICE_NAME
        self.version = settings.SERVICE_VERSION

        logger.info("PreprocessingServicer initialized")

    def HealthCheck(self, request, context):
        """Health check RPC."""
        # Import proto messages (generated from .proto file)
        try:
            from . import preprocessing_pb2
            return preprocessing_pb2.HealthResponse(
                healthy=True,
                version=self.version,
                service_name=self.service_name,
            )
        except ImportError:
            # Proto not compiled yet, return simple dict
            logger.warning("Proto files not compiled, returning basic health response")
            return {"healthy": True, "version": self.version, "service_name": self.service_name}

    def TokenizeAudio(self, request, context):
        """
        Tokenize audio into BPE tokens.

        Args:
            request: AudioRequest with audio_data, format, options.
            context: gRPC context.

        Returns:
            TokenResponse with tokens and features.
        """
        request_id = str(uuid.uuid4())
        logger.info(f"TokenizeAudio request (id={request_id})")

        try:
            # First convert audio to MIDI
            midi_result = self.audio_to_midi.convert(
                request.audio_data,
                audio_format=request.format or "wav",
            )

            # Then tokenize MIDI
            token_result = self.tokenizer.tokenize_midi(midi_result["midi_data"])

            # Build response
            try:
                from . import preprocessing_pb2
                return preprocessing_pb2.TokenResponse(
                    tokens=token_result["tokens"],
                    embeddings=token_result.get("embeddings", []),
                    embedding_dim=token_result.get("embedding_dim", 0),
                    features=token_result["features"],
                    request_id=request_id,
                )
            except ImportError:
                return {
                    "tokens": token_result["tokens"],
                    "embeddings": [],
                    "embedding_dim": 0,
                    "features": token_result["features"],
                    "request_id": request_id,
                }

        except Exception as e:
            logger.error(f"Error in TokenizeAudio: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    def TokenizeMidi(self, request, context):
        """
        Tokenize MIDI into BPE tokens.

        Args:
            request: MidiRequest with midi_data, options.
            context: gRPC context.

        Returns:
            TokenResponse with tokens and features.
        """
        request_id = str(uuid.uuid4())
        logger.info(f"TokenizeMidi request (id={request_id})")

        try:
            token_result = self.tokenizer.tokenize_midi(request.midi_data)

            try:
                from . import preprocessing_pb2
                return preprocessing_pb2.TokenResponse(
                    tokens=token_result["tokens"],
                    embeddings=token_result.get("embeddings", []),
                    embedding_dim=token_result.get("embedding_dim", 0),
                    features=token_result["features"],
                    request_id=request_id,
                )
            except ImportError:
                return {
                    "tokens": token_result["tokens"],
                    "embeddings": [],
                    "embedding_dim": 0,
                    "features": token_result["features"],
                    "request_id": request_id,
                }

        except Exception as e:
            logger.error(f"Error in TokenizeMidi: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    def ExtractFeatures(self, request, context):
        """
        Extract audio features.

        Args:
            request: AudioRequest with audio_data, format.
            context: gRPC context.

        Returns:
            FeaturesResponse with tempo, key, spectrogram, etc.
        """
        request_id = str(uuid.uuid4())
        logger.info(f"ExtractFeatures request (id={request_id})")

        try:
            # Extract features
            features = self.feature_extractor.extract_all(
                request.audio_data,
                audio_format=request.format or "wav",
            )

            # Generate mel spectrogram
            spec_result = self.spectrogram_generator.generate_mel_spectrogram(
                request.audio_data,
                audio_format=request.format or "wav",
            )

            # Extract chord progression
            import tempfile
            from pathlib import Path
            import librosa

            with tempfile.NamedTemporaryFile(suffix=f".{request.format or 'wav'}", delete=False) as f:
                f.write(request.audio_data)
                temp_path = Path(f.name)

            try:
                y, sr = librosa.load(temp_path, sr=22050, mono=True)
                chords = self.feature_extractor.extract_chord_progression(y, sr)
            finally:
                temp_path.unlink(missing_ok=True)

            try:
                from . import preprocessing_pb2
                return preprocessing_pb2.FeaturesResponse(
                    mel_spectrogram=spec_result["mel_spectrogram"],
                    n_mels=spec_result["n_mels"],
                    n_frames=spec_result["n_frames"],
                    tempo=features["tempo"],
                    key=features["key_string"],
                    time_signature=features["time_signature"],
                    chord_progression=chords,
                    duration=features["duration"],
                    extra_features={k: float(v) for k, v in features.items() if isinstance(v, (int, float))},
                    request_id=request_id,
                )
            except ImportError:
                return {
                    "mel_spectrogram": spec_result["mel_spectrogram"],
                    "n_mels": spec_result["n_mels"],
                    "n_frames": spec_result["n_frames"],
                    "tempo": features["tempo"],
                    "key": features["key_string"],
                    "time_signature": features["time_signature"],
                    "chord_progression": chords,
                    "duration": features["duration"],
                    "request_id": request_id,
                }

        except Exception as e:
            logger.error(f"Error in ExtractFeatures: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    def AudioToMidi(self, request, context):
        """
        Convert audio to MIDI.

        Args:
            request: AudioRequest with audio_data, format.
            context: gRPC context.

        Returns:
            MidiResponse with midi_data, notes, confidence.
        """
        request_id = str(uuid.uuid4())
        logger.info(f"AudioToMidi request (id={request_id})")

        try:
            result = self.audio_to_midi.convert(
                request.audio_data,
                audio_format=request.format or "wav",
            )

            # Convert notes to proto format
            try:
                from . import preprocessing_pb2
                notes = [
                    preprocessing_pb2.Note(
                        pitch=n["pitch"],
                        start_time=n["start_time"],
                        duration=n["duration"],
                        velocity=n["velocity"],
                    )
                    for n in result["notes"]
                ]

                return preprocessing_pb2.MidiResponse(
                    midi_data=result["midi_data"],
                    notes=notes,
                    confidence=result["confidence"],
                    request_id=request_id,
                )
            except ImportError:
                return {
                    "midi_data": result["midi_data"],
                    "notes": result["notes"],
                    "confidence": result["confidence"],
                    "request_id": request_id,
                }

        except Exception as e:
            logger.error(f"Error in AudioToMidi: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    def ReanalyzeSection(self, request, context):
        """
        Re-analyze a specific section of audio.

        Called by the Reasoning module when it needs more detailed analysis.

        Args:
            request: ReanalyzeRequest with audio_data, start/end times, focus_features.
            context: gRPC context.

        Returns:
            TokenResponse with refined analysis.
        """
        request_id = str(uuid.uuid4())
        logger.info(
            f"ReanalyzeSection request (id={request_id}): "
            f"{request.start_time}s - {request.end_time}s"
        )

        try:
            # For now, process the full audio
            # TODO: Implement audio slicing for specific sections

            midi_result = self.audio_to_midi.convert(
                request.audio_data,
                audio_format="wav",
            )

            token_result = self.tokenizer.tokenize_midi(midi_result["midi_data"])

            # Add focus features to results
            token_result["features"]["focus_features"] = list(request.focus_features)
            token_result["features"]["section_start"] = request.start_time
            token_result["features"]["section_end"] = request.end_time

            try:
                from . import preprocessing_pb2
                return preprocessing_pb2.TokenResponse(
                    tokens=token_result["tokens"],
                    embeddings=[],
                    embedding_dim=0,
                    features=token_result["features"],
                    request_id=request_id,
                )
            except ImportError:
                return {
                    "tokens": token_result["tokens"],
                    "embeddings": [],
                    "embedding_dim": 0,
                    "features": token_result["features"],
                    "request_id": request_id,
                }

        except Exception as e:
            logger.error(f"Error in ReanalyzeSection: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise


def serve_grpc(port: int = None):
    """
    Start the gRPC server.

    Args:
        port: Port to listen on. Defaults to config value.
    """
    settings = get_settings()
    port = port or settings.GRPC_PORT

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add servicer
    servicer = PreprocessingServicer()

    try:
        from . import preprocessing_pb2_grpc
        preprocessing_pb2_grpc.add_PreprocessingServiceServicer_to_server(
            servicer, server
        )
    except ImportError:
        logger.warning(
            "Proto files not compiled. Run: "
            "python -m grpc_tools.protoc -I protos "
            "--python_out=src/api/grpc --grpc_python_out=src/api/grpc "
            "protos/preprocessing.proto"
        )
        return

    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"gRPC server started on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)
        logger.info("gRPC server stopped")


if __name__ == "__main__":
    serve_grpc()
