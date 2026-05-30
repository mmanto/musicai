"""Pytest configuration and fixtures for MusicAI Preprocessing tests."""

import pytest
import allure
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = Path(__file__).parent.parent / "reports"


# ============== PYTEST CONFIGURATION ==============

def pytest_configure(config):
    """Configure pytest with markers and metadata."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "audio: audio processing tests")
    config.addinivalue_line("markers", "midi: MIDI processing tests")
    config.addinivalue_line("markers", "tokenizer: tokenization tests")


# ============== HOOKS FOR REPORTING ==============

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Enhance test reports with input/output data."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        # Attach fixture data as input
        _attach_fixture_data(item)

        # Attach captured output
        _attach_captured_output(report)


def _attach_fixture_data(item):
    """Attach fixture values to Allure report as test input."""
    if not hasattr(item, 'funcargs'):
        return

    fixture_data = {}
    for name, value in item.funcargs.items():
        # Skip internal fixtures
        if name.startswith('_') or name in ['request', 'capfd', 'capsys', 'caplog']:
            continue

        try:
            if isinstance(value, (str, int, float, bool)):
                fixture_data[name] = value
            elif isinstance(value, (list, dict)):
                fixture_data[name] = value
            elif isinstance(value, Path):
                fixture_data[name] = str(value)
            elif isinstance(value, bytes):
                fixture_data[name] = f"<bytes: {len(value)} bytes>"
            elif hasattr(value, '__dict__'):
                fixture_data[name] = f"{type(value).__name__}"
            else:
                fixture_data[name] = repr(value)[:200]
        except Exception:
            fixture_data[name] = f"<{type(value).__name__}>"

    if fixture_data:
        allure.attach(
            json.dumps(fixture_data, indent=2, default=str),
            name="Test Input (Fixtures)",
            attachment_type=allure.attachment_type.JSON
        )


def _attach_captured_output(report):
    """Attach captured stdout/stderr to report."""
    if hasattr(report, 'capstdout') and report.capstdout:
        allure.attach(
            report.capstdout,
            name="Captured stdout",
            attachment_type=allure.attachment_type.TEXT
        )

    if hasattr(report, 'capstderr') and report.capstderr:
        allure.attach(
            report.capstderr,
            name="Captured stderr",
            attachment_type=allure.attachment_type.TEXT
        )


def pytest_sessionfinish(session, exitstatus):
    """Write environment info for Allure report."""
    allure_results = REPORTS_DIR / "allure-results"
    if allure_results.exists():
        env_file = allure_results / "environment.properties"
        with open(env_file, "w") as f:
            f.write(f"Python={sys.version.split()[0]}\n")
            f.write(f"Platform={sys.platform}\n")
            f.write(f"Project=MusicAI Preprocessing\n")
            f.write(f"Version=0.1.0\n")
            f.write(f"Timestamp={datetime.now().isoformat()}\n")


@pytest.fixture(scope="session")
def test_data_dir():
    """Return the test data directory path."""
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def sample_wav_file():
    """Return path to sample WAV file."""
    return TEST_DATA_DIR / "Sombras dormidas.wav"


@pytest.fixture(scope="session")
def sample_mp3_file():
    """Return path to sample MP3 file."""
    return TEST_DATA_DIR / "Sombras dormidas.mp3"


@pytest.fixture(scope="session")
def sample_flac_file():
    """Return path to sample FLAC file."""
    return TEST_DATA_DIR / "Sombras dormidas.flac"


@pytest.fixture(scope="session")
def real_audio_bytes_wav(sample_wav_file):
    """Load real WAV audio file as bytes."""
    if sample_wav_file.exists():
        return sample_wav_file.read_bytes()
    return None


@pytest.fixture(scope="session")
def real_audio_bytes_mp3(sample_mp3_file):
    """Load real MP3 audio file as bytes."""
    if sample_mp3_file.exists():
        return sample_mp3_file.read_bytes()
    return None


@pytest.fixture(scope="session")
def real_audio_bytes_flac(sample_flac_file):
    """Load real FLAC audio file as bytes."""
    if sample_flac_file.exists():
        return sample_flac_file.read_bytes()
    return None


@pytest.fixture(scope="session")
def sample_audio_data():
    """Generate sample audio data for testing."""
    import numpy as np

    # Generate simple sine wave
    sample_rate = 22050
    duration = 1.0
    frequency = 440  # A4

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)

    # Convert to bytes (16-bit PCM)
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16.tobytes()


@pytest.fixture(scope="session")
def sample_midi_data():
    """Generate sample MIDI data for testing."""
    # Simple MIDI file with one note
    # This is a minimal MIDI file structure
    midi_bytes = bytes([
        # Header chunk
        0x4D, 0x54, 0x68, 0x64,  # "MThd"
        0x00, 0x00, 0x00, 0x06,  # Length = 6
        0x00, 0x00,              # Format = 0
        0x00, 0x01,              # Number of tracks = 1
        0x00, 0x60,              # Division = 96 PPQ

        # Track chunk
        0x4D, 0x54, 0x72, 0x6B,  # "MTrk"
        0x00, 0x00, 0x00, 0x14,  # Length

        # Note on C4
        0x00, 0x90, 0x3C, 0x64,  # Delta=0, Note On, pitch=60, velocity=100

        # Note off C4
        0x60, 0x80, 0x3C, 0x00,  # Delta=96, Note Off, pitch=60

        # End of track
        0x00, 0xFF, 0x2F, 0x00,
    ])
    return midi_bytes
