"""
Profile Processor - Middleware for profile extraction in chat flow.

Scoop AI Hybrid Memory System
Integrates ProfileExtractor with chat endpoints for automatic profile updates.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from app.profile.profile_extractor import (
    ProfileExtractor, 
    ExtractionResult, 
    has_negation,
    has_context_reference,
    verify_fact_with_llm
)
from app.memory.mongo_store import UserStore

logger = logging.getLogger(__name__)


@dataclass
class ProfileProcessingResult:
    """Result of profile processing from a message."""
    extraction: Optional[ExtractionResult] = None
    demographics_updated: bool = False
    physical_stats_updated: bool = False
    facts_added: int = 0
    error: Optional[str] = None


async def _verify_extractions_with_llm(
    message: str, 
    extraction: ExtractionResult
) -> ExtractionResult:
    """
    Verify extracted values using LLM when negation is detected.
    
    This is called ONLY when has_negation() returns True.
    Modifies extraction in-place, removing incorrect values.
    """
    # Verify age if extracted
    if extraction.demographics.get("age"):
        verified_age = await verify_fact_with_llm(
            text=message,
            field="age",
            extracted_value=extraction.demographics["age"]
        )
        if verified_age is None:
            # LLM rejected this extraction
            del extraction.demographics["age"]
            logger.info("🔍 Age extraction rejected by LLM")
        elif verified_age != extraction.demographics["age"]:
            # LLM corrected the value
            extraction.demographics["age"] = verified_age
    
    # Verify weight if extracted
    if extraction.physical_stats.get("weight"):
        verified_weight = await verify_fact_with_llm(
            text=message,
            field="weight",
            extracted_value=extraction.physical_stats["weight"]
        )
        if verified_weight is None:
            del extraction.physical_stats["weight"]
            logger.info("🔍 Weight extraction rejected by LLM")
        elif verified_weight != extraction.physical_stats["weight"]:
            extraction.physical_stats["weight"] = verified_weight
    
    # Update has_updates flag
    extraction.has_updates = bool(
        extraction.demographics or 
        extraction.physical_stats or 
        extraction.potential_facts
    )
    
    return extraction


async def process_user_message(
    user_id: str,
    message: str,
    user_store: UserStore,
    extractor: Optional[ProfileExtractor] = None
) -> ProfileProcessingResult:
    """
    Extract profile data from user message and store updates.
    
    This is non-blocking - failures are logged but don't affect chat flow.
    
    Args:
        user_id: User ID from session
        message: User message text (Georgian supported)
        user_store: UserStore instance for persistence
        extractor: Optional ProfileExtractor (created if not provided)
        
    Returns:
        ProfileProcessingResult with extraction details
    """
    result = ProfileProcessingResult()
    
    try:
        # Initialize extractor if not provided
        if extractor is None:
            extractor = ProfileExtractor()
        
        # Extract profile data from message (RegEx - fast, sync)
        extraction = extractor.extract(message)
        
        # LLM VERIFICATION: If negation detected, verify with Gemini
        if extraction.has_updates and has_negation(message):
            logger.info(f"🔍 Negation detected, verifying with LLM...")
            extraction = await _verify_extractions_with_llm(message, extraction)
        
        # Context check: If referencing others (child, sibling), skip entirely
        if extraction.has_updates and has_context_reference(message):
            logger.info(f"⚠️ Context reference detected (other person), skipping extraction")
            extraction = ExtractionResult()  # Clear all extractions
        
        result.extraction = extraction
        
        # Skip if no updates detected
        if not extraction.has_updates:
            logger.debug(f"👤 No profile updates in message for user={user_id}")
            return result
        
        logger.info(f"👤 Profile extraction found updates for user={user_id}")
        
        # Store demographics updates
        if extraction.demographics:
            success = await user_store.update_demographics(
                user_id=user_id,
                updates=extraction.demographics
            )
            result.demographics_updated = success
            if success:
                logger.info(f"✅ Demographics updated: {list(extraction.demographics.keys())}")
        
        # Store physical stats updates (height, weight use different methods)
        if extraction.physical_stats:
            stats_success = True
            
            # Weight uses versioned add_weight_entry()
            if "weight" in extraction.physical_stats:
                try:
                    await user_store.add_weight_entry(
                        user_id=user_id,
                        weight=extraction.physical_stats["weight"]
                    )
                    logger.info(f"✅ Weight entry added: {extraction.physical_stats['weight']} kg")
                except Exception as e:
                    logger.error(f"❌ Failed to add weight entry: {e}")
                    stats_success = False
            
            # Height/body_fat use update_physical_stats()
            if "height" in extraction.physical_stats:
                await user_store.update_physical_stats(
                    user_id=user_id,
                    height=extraction.physical_stats.get("height"),
                    body_fat_percent=extraction.physical_stats.get("body_fat_percent")
                )
                logger.info(f"✅ Height updated: {extraction.physical_stats.get('height')} cm")
            
            result.physical_stats_updated = stats_success
        
        # Store potential facts (deferred: requires embedding)
        # TODO: Call Voyage AI for embeddings before storing facts
        if extraction.potential_facts:
            logger.info(f"📝 Potential facts detected: {len(extraction.potential_facts)} (embedding deferred)")
        
        # Log confirmations needed (sensitive data)
        if extraction.confirmations:
            logger.info(f"⚠️ Confirmations pending: {extraction.confirmations}")
        
    except Exception as e:
        # Non-blocking: log and continue
        logger.error(f"❌ Profile processing error for user={user_id}: {e}")
        result.error = str(e)
    
    return result
