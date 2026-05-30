"""Tests for Neo4j client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from neo4j import GraphDatabase

from src.graph.neo4j_client import Neo4jClient


class TestNeo4jClient:
    """Test Neo4j client functionality."""

    @patch('src.graph.neo4j_client.GraphDatabase.driver')
    def test_connect_success(self, mock_driver):
        """Test successful connection to Neo4j."""
        # Setup
        mock_driver_instance = MagicMock()
        mock_session = MagicMock()
        mock_driver.return_value = mock_driver_instance
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session

        client = Neo4jClient()

        # Execute
        client.connect()

        # Assert
        assert client._driver is not None
        mock_driver.assert_called_once()
        mock_session.run.assert_called_once_with("RETURN 1")

    @patch('src.graph.neo4j_client.GraphDatabase.driver')
    def test_connect_failure(self, mock_driver):
        """Test connection failure handling."""
        # Setup
        mock_driver.side_effect = Exception("Connection failed")
        client = Neo4jClient()

        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            client.connect()

        assert "Connection failed" in str(exc_info.value)

    def test_close_connection(self):
        """Test closing Neo4j connection."""
        client = Neo4jClient()
        mock_driver = MagicMock()
        client._driver = mock_driver

        # Execute
        client.close()

        # Assert
        mock_driver.close.assert_called_once()

    @patch('src.graph.neo4j_client.GraphDatabase.driver')
    def test_execute_query(self, mock_driver):
        """Test query execution."""
        # Setup
        mock_driver_instance = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()

        mock_driver.return_value = mock_driver_instance
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = mock_result

        # Mock result records
        mock_record1 = MagicMock()
        mock_record1.data.return_value = {"name": "C", "midi_number": 60}
        mock_record2 = MagicMock()
        mock_record2.data.return_value = {"name": "D", "midi_number": 62}
        mock_result.__iter__.return_value = [mock_record1, mock_record2]

        client = Neo4jClient()
        client._driver = mock_driver_instance

        # Execute
        query = "MATCH (n:Note) RETURN n"
        results = client.execute_query(query)

        # Assert
        assert len(results) == 2
        assert results[0]["name"] == "C"
        assert results[1]["midi_number"] == 62

    @patch('src.graph.neo4j_client.GraphDatabase.driver')
    def test_create_node(self, mock_driver):
        """Test node creation."""
        # Setup
        mock_driver_instance = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = MagicMock()

        mock_driver.return_value = mock_driver_instance
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = mock_result
        mock_record.data.return_value = {"n": {"name": "C", "midi_number": 60}}
        mock_result.__iter__.return_value = [mock_record]

        client = Neo4jClient()
        client._driver = mock_driver_instance

        # Execute
        node = client.create_node("Note", {"name": "C", "midi_number": 60})

        # Assert
        assert node is not None
        assert "name" in node

    @patch('src.graph.neo4j_client.GraphDatabase.driver')
    def test_search_by_concept(self, mock_driver):
        """Test concept search with fuzzy matching."""
        # Setup
        mock_driver_instance = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = MagicMock()

        mock_driver.return_value = mock_driver_instance
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = mock_result
        mock_record.data.return_value = {"n": {"name": "Major", "quality": "Major"}}
        mock_result.__iter__.return_value = [mock_record]

        client = Neo4jClient()
        client._driver = mock_driver_instance

        # Execute
        results = client.search_by_concept("major", limit=5)

        # Assert
        assert len(results) == 1
        assert results[0]["n"]["name"] == "Major"

    @patch('src.graph.neo4j_client.GraphDatabase.driver')
    def test_get_shortest_path(self, mock_driver):
        """Test shortest path finding."""
        # Setup
        mock_driver_instance = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = MagicMock()

        mock_driver.return_value = mock_driver_instance
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = mock_result
        mock_record.data.return_value = {"path": ["C", "G"], "distance": 1}
        mock_result.__iter__.return_value = [mock_record]

        client = Neo4jClient()
        client._driver = mock_driver_instance

        # Execute
        path = client.get_shortest_path("node-1", "node-2")

        # Assert
        assert path is not None
        assert "distance" in path

    @patch('src.graph.neo4j_client.GraphDatabase.driver')
    def test_clear_database(self, mock_driver):
        """Test database clearing."""
        # Setup
        mock_driver_instance = MagicMock()
        mock_session = MagicMock()

        mock_driver.return_value = mock_driver_instance
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session

        client = Neo4jClient()
        client._driver = mock_driver_instance

        # Execute
        client.clear_database()

        # Assert
        mock_session.run.assert_called()
        call_args = mock_session.run.call_args[0][0]
        assert "DETACH DELETE" in call_args
