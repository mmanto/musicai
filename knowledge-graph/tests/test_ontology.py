"""Tests for Music Ontology."""

import pytest
from unittest.mock import Mock, MagicMock

from src.graph.ontology import MusicOntology, NodeType, RelationType


class TestMusicOntology:
    """Test Music Ontology functionality."""

    def test_node_types_enum(self):
        """Test NodeType enum contains expected values."""
        assert NodeType.NOTE == "Note"
        assert NodeType.CHORD == "Chord"
        assert NodeType.SCALE == "Scale"
        assert NodeType.KEY == "Key"
        assert NodeType.GENRE == "Genre"

    def test_relationship_types_enum(self):
        """Test RelationType enum contains expected values."""
        assert RelationType.CONTAINS == "CONTAINS"
        assert RelationType.FOLLOWS == "FOLLOWS"
        assert RelationType.RESOLVES_TO == "RESOLVES_TO"
        assert RelationType.SIMILAR_TO == "SIMILAR_TO"

    def test_initialize_ontology(self, mock_neo4j_client):
        """Test ontology initialization."""
        # Setup
        ontology = MusicOntology(mock_neo4j_client)

        # Execute
        ontology.initialize()

        # Assert - check that execute_query was called multiple times
        assert mock_neo4j_client.execute_query.call_count > 0

    def test_populate_notes(self, mock_neo4j_client):
        """Test note population."""
        # Setup
        ontology = MusicOntology(mock_neo4j_client)

        # Execute
        ontology._populate_notes()

        # Assert
        mock_neo4j_client.execute_query.assert_called()
        call_args = mock_neo4j_client.execute_query.call_args
        query = call_args[0][0]
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]

        assert "MERGE" in query or "CREATE" in query
        assert "notes" in params or "notes" in query.lower()

    def test_populate_scales(self, mock_neo4j_client):
        """Test scale population."""
        # Setup
        ontology = MusicOntology(mock_neo4j_client)

        # Execute
        ontology._populate_scales()

        # Assert
        mock_neo4j_client.execute_query.assert_called()
        call_args = mock_neo4j_client.execute_query.call_args
        query = call_args[0][0]

        assert "Scale" in query

    def test_populate_chords(self, mock_neo4j_client):
        """Test chord population."""
        # Setup
        ontology = MusicOntology(mock_neo4j_client)

        # Execute
        ontology._populate_chords()

        # Assert
        mock_neo4j_client.execute_query.assert_called()

    def test_query_related_concepts(self, mock_neo4j_client):
        """Test querying related concepts."""
        # Setup
        mock_neo4j_client.execute_query.return_value = [
            {"related": {"name": "Minor", "quality": "Minor"}, "r": None}
        ]
        ontology = MusicOntology(mock_neo4j_client)

        # Execute
        results = ontology.query_related_concepts("Major", max_depth=2)

        # Assert
        assert len(results) == 1
        assert results[0]["related"]["name"] == "Minor"

    def test_query_related_concepts_with_relationship_type(self, mock_neo4j_client):
        """Test querying related concepts with specific relationship."""
        # Setup
        mock_neo4j_client.execute_query.return_value = []
        ontology = MusicOntology(mock_neo4j_client)

        # Execute
        results = ontology.query_related_concepts(
            "Tonic",
            relationship_type="FOLLOWS",
            max_depth=1
        )

        # Assert
        mock_neo4j_client.execute_query.assert_called()
        call_args = mock_neo4j_client.execute_query.call_args
        query = call_args[0][0]

        assert "FOLLOWS" in query

    def test_get_scale_chords(self, mock_neo4j_client):
        """Test getting chords for a scale."""
        # Setup
        mock_neo4j_client.execute_query.return_value = [
            {"c": {"name": "C Major", "intervals": [0, 4, 7]}}
        ]
        ontology = MusicOntology(mock_neo4j_client)

        # Execute
        results = ontology.get_scale_chords("Major")

        # Assert
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called()

    def test_get_chord_progressions(self, mock_neo4j_client):
        """Test getting chord progressions for a genre."""
        # Setup
        mock_neo4j_client.execute_query.return_value = [
            {"p": {"formula": "I-IV-V-I", "name": "Common Progression"}}
        ]
        ontology = MusicOntology(mock_neo4j_client)

        # Execute
        results = ontology.get_chord_progressions("Jazz")

        # Assert
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called()
