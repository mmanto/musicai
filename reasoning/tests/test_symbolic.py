"""Tests for symbolic reasoning components."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestMusic21Analyzer:
    """Tests for Music21Analyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        from src.symbolic.music21_analyzer import Music21Analyzer
        return Music21Analyzer()

    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initializes correctly."""
        assert analyzer is not None

    @patch('src.symbolic.music21_analyzer.converter')
    def test_analyze_score_musicxml(self, mock_converter, analyzer, sample_musicxml):
        """Test analyzing MusicXML score."""
        # Mock music21 score
        mock_score = MagicMock()
        mock_score.analyze.return_value = Mock(tonic=Mock(name='C'), mode='major')
        mock_converter.parse.return_value = mock_score

        result = analyzer.analyze_score(sample_musicxml, 'musicxml')

        assert isinstance(result, dict)
        mock_converter.parse.assert_called_once()

    def test_analyze_score_invalid_format(self, analyzer):
        """Test analyzing with invalid format."""
        with pytest.raises(ValueError):
            analyzer.analyze_score(b"data", 'invalid_format')

    @patch('src.symbolic.music21_analyzer.converter')
    def test_extract_key_info(self, mock_converter, analyzer, sample_musicxml):
        """Test key extraction."""
        mock_score = MagicMock()
        mock_key = Mock()
        mock_key.tonic.name = 'C'
        mock_key.mode = 'major'
        mock_score.analyze.return_value = mock_key
        mock_converter.parse.return_value = mock_score

        result = analyzer.analyze_score(sample_musicxml, 'musicxml')

        assert 'key' in result or 'harmony' in result


class TestRulesEngine:
    """Tests for RulesEngine."""

    @pytest.fixture
    def rules_engine(self):
        """Create rules engine instance."""
        from src.symbolic.rules_engine import RulesEngine
        return RulesEngine()

    def test_rules_engine_initialization(self, rules_engine):
        """Test rules engine initializes with rules."""
        assert rules_engine is not None
        rules = rules_engine.list_rules()
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_list_rules_no_filter(self, rules_engine):
        """Test listing all rules."""
        rules = rules_engine.list_rules()
        assert isinstance(rules, list)
        assert all('name' in rule for rule in rules)
        assert all('category' in rule for rule in rules)

    def test_list_rules_by_category(self, rules_engine):
        """Test filtering rules by category."""
        categories = rules_engine.get_categories()
        if categories:
            category = categories[0]
            rules = rules_engine.list_rules(category=category)
            assert all(rule['category'] == category for rule in rules)

    def test_list_rules_enabled_only(self, rules_engine):
        """Test listing only enabled rules."""
        rules = rules_engine.list_rules(enabled_only=True)
        assert all(rule['enabled'] for rule in rules)

    def test_get_categories(self, rules_engine):
        """Test getting rule categories."""
        categories = rules_engine.get_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_enable_disable_rule(self, rules_engine):
        """Test enabling/disabling rules."""
        rules = rules_engine.list_rules()
        if rules:
            rule_name = rules[0]['name']

            # Disable
            rules_engine.disable_rule(rule_name)
            rule = next((r for r in rules_engine.list_rules() if r['name'] == rule_name), None)
            assert rule is not None
            assert not rule['enabled']

            # Enable
            rules_engine.enable_rule(rule_name)
            rule = next((r for r in rules_engine.list_rules() if r['name'] == rule_name), None)
            assert rule is not None
            assert rule['enabled']

    def test_validate_with_mock_analysis(self, rules_engine):
        """Test validation with mock analysis."""
        mock_analysis = {
            "key": "C major",
            "harmony": {"chords": ["C", "G", "Am", "F"]},
            "melody": {"range": "C4-C5"}
        }

        from src.symbolic.rules_engine import RuleSeverity
        result = rules_engine.validate(mock_analysis, min_severity=RuleSeverity.INFO)

        assert isinstance(result, dict)
        assert 'passed' in result or 'violations' in result
