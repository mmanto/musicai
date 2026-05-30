"""Basic functional tests for symbolic reasoning components."""

import pytest


class TestRulesEngineBasic:
    """Basic tests for RulesEngine without external dependencies."""

    def test_rules_engine_can_be_imported(self):
        """Test that RulesEngine can be imported."""
        from src.symbolic.rules_engine import RulesEngine
        assert RulesEngine is not None

    def test_rules_engine_initialization(self):
        """Test rules engine initializes with default rules."""
        from src.symbolic.rules_engine import RulesEngine

        engine = RulesEngine()
        assert engine is not None

    def test_list_all_rules(self):
        """Test listing all rules."""
        from src.symbolic.rules_engine import RulesEngine

        engine = RulesEngine()
        rules = engine.list_rules()

        assert isinstance(rules, list)
        assert len(rules) > 0

        # Check first rule has required fields
        first_rule = rules[0]
        assert 'name' in first_rule
        assert 'description' in first_rule
        assert 'category' in first_rule
        assert 'severity' in first_rule
        assert 'enabled' in first_rule

    def test_get_categories(self):
        """Test getting rule categories."""
        from src.symbolic.rules_engine import RulesEngine

        engine = RulesEngine()
        categories = engine.get_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert 'voice_leading' in categories
        assert 'harmony' in categories

    def test_filter_rules_by_category(self):
        """Test filtering rules by category."""
        from src.symbolic.rules_engine import RulesEngine

        engine = RulesEngine()
        voice_leading_rules = engine.list_rules(category='voice_leading')

        assert isinstance(voice_leading_rules, list)
        assert all(rule['category'] == 'voice_leading' for rule in voice_leading_rules)

    def test_enable_disable_rule(self):
        """Test enabling and disabling a rule."""
        from src.symbolic.rules_engine import RulesEngine

        engine = RulesEngine()
        rules = engine.list_rules()

        if rules:
            rule_name = rules[0]['name']

            # Disable the rule
            engine.disable_rule(rule_name)
            updated_rules = engine.list_rules()
            disabled_rule = next(r for r in updated_rules if r['name'] == rule_name)
            assert not disabled_rule['enabled']

            # Enable the rule
            engine.enable_rule(rule_name)
            updated_rules = engine.list_rules()
            enabled_rule = next(r for r in updated_rules if r['name'] == rule_name)
            assert enabled_rule['enabled']

    def test_rule_severity_enum(self):
        """Test RuleSeverity enum."""
        from src.symbolic.rules_engine import RuleSeverity

        assert RuleSeverity.INFO.value == 'info'
        assert RuleSeverity.LOW.value == 'low'
        assert RuleSeverity.MEDIUM.value == 'medium'
        assert RuleSeverity.HIGH.value == 'high'
        assert RuleSeverity.CRITICAL.value == 'critical'


class TestMusic21AnalyzerBasic:
    """Basic tests for Music21Analyzer."""

    def test_analyzer_can_be_imported(self):
        """Test that Music21Analyzer can be imported."""
        from src.symbolic.music21_analyzer import Music21Analyzer
        assert Music21Analyzer is not None

    def test_analyzer_initialization(self):
        """Test analyzer initializes correctly."""
        from src.symbolic.music21_analyzer import Music21Analyzer

        analyzer = Music21Analyzer()
        assert analyzer is not None

    def test_supported_formats(self):
        """Test analyzer has supported formats defined."""
        from src.symbolic.music21_analyzer import Music21Analyzer

        analyzer = Music21Analyzer()

        # These are the formats that should be supported
        supported_formats = ['musicxml', 'midi', 'abc', 'mei']

        # At least some basic formats should work
        assert hasattr(analyzer, 'analyze_score')


class TestConfigurationBasic:
    """Basic tests for configuration."""

    def test_settings_can_be_imported(self):
        """Test settings can be imported."""
        from src.config import Settings, get_settings
        assert Settings is not None
        assert get_settings is not None

    def test_settings_has_defaults(self):
        """Test settings have sensible defaults."""
        from src.config import get_settings

        settings = get_settings()

        assert settings.SERVICE_NAME == 'reasoning'
        assert settings.REST_PORT == 8004
        assert settings.GRPC_PORT == 50054
        assert settings.OLLAMA_MODEL is not None
        assert settings.COT_MAX_STEPS > 0
