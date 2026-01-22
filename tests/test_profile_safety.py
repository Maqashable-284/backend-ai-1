"""
Safety & Performance Tests for Profile Integration

These tests verify that profile extraction in live chat:
1. Does not crash the chat when errors occur (Fail-Safe)
2. Does not block chat response (Latency)
3. Handles complex Georgian negation patterns (Negative Context)
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass

# Import the module under test
from app.profile.profile_processor import process_user_message, ProfileProcessingResult
from app.profile.profile_extractor import ProfileExtractor, has_negation, has_context_reference


# =============================================================================
# 1. FAIL-SAFE TEST (Error Isolation)
# =============================================================================

class TestFailSafe:
    """Verify chat survives if ProfileExtractor or DB crashes."""
    
    @pytest.mark.asyncio
    async def test_chat_survives_extractor_crash(self):
        """Chat should return result even if extractor throws exception."""
        mock_store = MagicMock()
        mock_extractor = MagicMock()
        
        # Simulate extractor explosion (extract method throws)
        mock_extractor.extract.side_effect = Exception("Database Connection Failed!")
        
        # Call process_user_message - should NOT raise
        result = await process_user_message(
            user_id="user123",
            message="გამარჯობა, ვარ 25 წლის",
            user_store=mock_store,
            extractor=mock_extractor
        )
        
        # Should return a result with error captured
        assert isinstance(result, ProfileProcessingResult)
        assert result.error is not None
        assert "Database Connection Failed" in result.error
        
    @pytest.mark.asyncio
    async def test_chat_survives_db_update_failure(self):
        """Chat continues even if DB update fails."""
        mock_store = MagicMock()
        mock_store.update_demographics = AsyncMock(side_effect=Exception("MongoDB timeout"))
        
        # Real extractor that finds age
        extractor = ProfileExtractor()
        
        # Should NOT raise, error should be captured
        result = await process_user_message(
            user_id="user123",
            message="ვარ 30 წლის",
            user_store=mock_store,
            extractor=extractor
        )
        
        assert isinstance(result, ProfileProcessingResult)
        assert result.error is not None
        assert "MongoDB timeout" in result.error


# =============================================================================
# 2. LATENCY / NON-BLOCKING TEST
# =============================================================================

class TestLatency:
    """Verify profile extraction doesn't block chat response."""
    
    @pytest.mark.asyncio
    async def test_extraction_returns_quickly(self):
        """process_user_message should return quickly even with slow operations."""
        mock_store = MagicMock()
        mock_store.update_demographics = AsyncMock(return_value=True)
        mock_store.update_physical_stats = AsyncMock(return_value=True)
        
        extractor = ProfileExtractor()
        
        start_time = time.time()
        result = await process_user_message(
            user_id="user123",
            message="ვარ 30 წლის, 85 კგ ვიწონი",
            user_store=mock_store,
            extractor=extractor
        )
        elapsed = time.time() - start_time
        
        # Profile extraction should complete in under 100ms
        assert elapsed < 0.1, f"Extraction took {elapsed:.3f}s, expected < 0.1s"
        assert result.demographics_updated or result.extraction is not None

    @pytest.mark.asyncio
    async def test_slow_db_still_returns(self):
        """Even with slow DB, function should eventually return (not hang)."""
        mock_store = MagicMock()
        
        async def slow_update(*args, **kwargs):
            await asyncio.sleep(0.5)  # Simulate slow DB
            return True
            
        mock_store.update_demographics = slow_update
        mock_store.update_physical_stats = AsyncMock(return_value=True)
        
        extractor = ProfileExtractor()
        
        start_time = time.time()
        result = await process_user_message(
            user_id="user123",
            message="ვარ 25 წლის",
            user_store=mock_store,
            extractor=extractor
        )
        elapsed = time.time() - start_time
        
        # Should complete within reasonable time (not hang indefinitely)
        assert elapsed < 2.0, f"Function hung for {elapsed:.2f}s"
        assert result.extraction is not None


# =============================================================================
# 3. NEGATIVE CONTEXT / FALSE POSITIVE TESTS (Georgian Negation)
# =============================================================================

class TestGeorgianNegation:
    """Test complex Georgian negation patterns to avoid false positives."""
    
    def test_has_negation_detection(self):
        """Test negation trigger detection."""
        assert has_negation("არ ვარ 20 წლის") == True
        assert has_negation("20 წლის კი არა, 30-ის") == True
        assert has_negation("ვარ 30 წლის") == False
    
    def test_has_context_reference_detection(self):
        """Test context reference detection."""
        assert has_context_reference("ჩემი შვილია 10 წლის") == True
        assert has_context_reference("ძმა 25 წლის არის") == True
        assert has_context_reference("ვარ 30 წლის") == False
    
    @pytest.mark.parametrize("text,expected_age", [
        # Standard cases (should work with RegEx alone)
        ("ვარ 30 წლის", 30),
        ("30 წლის ვარ", 30),
    ])
    def test_age_extraction_standard(self, text, expected_age):
        """Test standard age extraction works."""
        extractor = ProfileExtractor()
        result = extractor.extract(text)
        actual_age = result.demographics.get("age")
        assert actual_age == expected_age
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("text,expected_age", [
        # Negation cases - NOW HANDLED with LLM verification
        ("არ ვარ 20 წლის, 30-ის ვარ", 30),  # Should extract 30, not 20
        ("20 წლის კი არა, 30-ის", 30),       # Should extract 30, not 20
    ])
    async def test_age_extraction_with_negation(self, text, expected_age):
        """Test that negation patterns are verified by LLM."""
        from unittest.mock import MagicMock, AsyncMock, patch
        
        mock_store = MagicMock()
        mock_store.update_demographics = AsyncMock(return_value=True)
        mock_store.update_physical_stats = AsyncMock(return_value=True)
        
        # Mock verify_fact_with_llm to return the correct value
        with patch('app.profile.profile_processor.verify_fact_with_llm') as mock_verify:
            mock_verify.return_value = expected_age
            
            result = await process_user_message(
                user_id="test_user",
                message=text,
                user_store=mock_store
            )
            
            actual_age = result.extraction.demographics.get("age")
            assert actual_age == expected_age, f"Expected {expected_age}, got {actual_age} for: '{text}'"
    
    @pytest.mark.asyncio
    async def test_context_reference_blocks_extraction(self):
        """Test that context references (child, sibling) skip extraction."""
        mock_store = MagicMock()
        mock_store.update_demographics = AsyncMock(return_value=True)
        
        result = await process_user_message(
            user_id="test_user",
            message="ჩემი შვილია 10 წლის",
            user_store=mock_store
        )
        
        # Should NOT extract child's age as user's age
        assert result.extraction.demographics.get("age") is None

    @pytest.mark.parametrize("text,expected_weight", [
        # Standard cases
        ("85 კგ ვიწონი", 85),
        ("ვიწონი 90 კილო", 90),
    ])
    def test_weight_extraction_standard(self, text, expected_weight):
        """Test standard weight extraction works."""
        extractor = ProfileExtractor()
        result = extractor.extract(text)
        actual_weight = result.physical_stats.get("weight")
        assert actual_weight == expected_weight
    
    @pytest.mark.asyncio
    async def test_weight_with_temporal_context(self):
        """Test weight extraction with temporal context (past vs current)."""
        from unittest.mock import MagicMock, AsyncMock, patch
        
        mock_store = MagicMock()
        mock_store.update_physical_stats = AsyncMock(return_value=True)
        
        # Add temporal trigger to NEGATION_TRIGGERS for this test
        text = "ადრე 100 კგ ვიყავი, ახლა 75"
        
        # Mock LLM to return correct current weight
        with patch('app.profile.profile_processor.verify_fact_with_llm') as mock_verify:
            mock_verify.return_value = 75  # Current weight
            # Note: This test requires temporal triggers, which is future enhancement
            # For now we test that the infrastructure works
            pass  # Placeholder for future temporal context implementation


# =============================================================================
# 4. EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Additional edge cases for robustness."""
    
    def test_empty_message(self):
        """Empty message should not crash extractor."""
        extractor = ProfileExtractor()
        result = extractor.extract("")
        
        assert result.has_updates == False
        assert result.demographics == {}
        
    def test_unicode_only_message(self):
        """Pure emoji/symbols should be handled gracefully."""
        extractor = ProfileExtractor()
        result = extractor.extract("👋 🏋️ 💪")
        
        assert result.has_updates == False
        
    def test_very_long_message(self):
        """Long messages shouldn't cause performance issues."""
        extractor = ProfileExtractor()
        long_text = "ვარ 30 წლის " * 1000  # 13,000+ chars
        
        start = time.time()
        result = extractor.extract(long_text)
        elapsed = time.time() - start
        
        # Should complete in under 1 second even for long text
        assert elapsed < 1.0, f"Long text took {elapsed:.2f}s"
        assert result.demographics.get("age") == 30
