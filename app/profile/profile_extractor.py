"""
Profile Extractor - Extracts structured and semantic data from user messages.

Implements:
1. RegEx extraction for structured fields (age, weight, height)
2. LLM classification for semantic facts
3. Occupation categorization
4. Confirmation generation for sensitive facts

Georgian patterns supported:
- Age: "40 წლის", "40 წ"
- Weight: "85 კგ", "85 კილო"
- Height: "180 სმ", "180 სანტი"
- Occupation: "ბანკში ვმუშაობ", "ბანკირი ვარ"
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# LATIN → GEORGIAN TRANSLITERATION
# =============================================================================

# Common Latin phonetic spellings → Georgian equivalents
LATIN_TO_GEORGIAN = {
    # Age-related
    "wlis": "წლის",
    "weli": "წელი",
    "wl": "წ",
    # Weight-related  
    "kg": "კგ",
    "kilo": "კილო",
    "viwoni": "ვიწონი",
    "wona": "წონა",
    # Height-related
    "sm": "სმ",
    "santi": "სანტი",
    "santimetri": "სანტიმეტრი",
    "simaghle": "სიმაღლე",
    # Common verbs
    "var": "ვარ",
    "vmushaobi": "ვმუშაობ",
    "vmushaoб": "ვმუშაობ",
    "maqvs": "მაქვს",
    "minda": "მინდა",
    # Occupation keywords
    "bankshi": "ბანკში",
    "mzareuli": "მზარეული",
    "programisti": "პროგრამისტი",
    "mdzgholi": "მძღოლი",
    "mshenebeli": "მშენებელი",
    "ofisshi": "ოფისში",
}


def apply_transliteration(text: str) -> str:
    """
    Convert common Latin phonetic spellings to Georgian.
    
    This allows users to type in Latin script while enabling
    RegEx patterns to match Georgian keywords.
    
    Example:
        "50 wlis var" → "50 წლის ვარ"
    """
    result = text.lower()
    
    # Sort by length descending to match longer phrases first
    for latin, georgian in sorted(LATIN_TO_GEORGIAN.items(), key=lambda x: -len(x[0])):
        result = result.replace(latin, georgian)
    
    return result

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExtractionResult:
    """Result of profile extraction from a message."""
    demographics: Dict[str, Any] = field(default_factory=dict)
    physical_stats: Dict[str, Any] = field(default_factory=dict)
    lifestyle: Dict[str, Any] = field(default_factory=dict)
    potential_facts: List[str] = field(default_factory=list)
    confirmations: List[str] = field(default_factory=list)
    has_updates: bool = False


# =============================================================================
# REGEX PATTERNS (Georgian)
# =============================================================================

# Age patterns: "40 წლის", "40წ", "ვარ 40 წლის"
AGE_PATTERNS = [
    r'(\d{1,2})\s*წლის',           # 40 წლის
    r'(\d{1,2})\s*წ(?:[^\w]|$)',   # 40წ (with non-word or end-of-string)
    r'ვარ\s*(\d{1,2})\s*წლის',     # ვარ 40 წლის
    r'(\d{1,2})\s*წლის\s*ვარ',     # 40 წლის ვარ
]

# Weight patterns: "85 კგ", "85 კილო", "ვიწონი 85"
WEIGHT_PATTERNS = [
    r'(\d{2,3})\s*კგ',             # 85 კგ
    r'(\d{2,3})\s*კილო',           # 85 კილო
    r'ვიწონი\s*(\d{2,3})',         # ვიწონი 85
    r'წონა.*?(\d{2,3})',           # წონა 85
]

# Height patterns: "180 სმ", "180 სანტი"
HEIGHT_PATTERNS = [
    r'(\d{3})\s*სმ',               # 180 სმ
    r'(\d{3})\s*სანტი',            # 180 სანტი
    r'სიმაღლე.*?(\d{3})',          # სიმაღლე 180
]

# Occupation keywords → category mapping
OCCUPATION_KEYWORDS = {
    "sedentary": [
        "ბანკ", "ოფის", "კომპიუტერ", "პროგრამ", "ბუღალტ", 
        "იურისტ", "ადვოკატ", "მენეჯერ", "სექრეტარ", "დიზაინერ",
        "it-", "აითი", "დეველოპერ", "ინჟინერ"  # IT sector
    ],
    "light": [
        "მაღაზია", "გამყიდველ", "მასწავლებ", "ექიმ", "ექთან",
        "მზარეულ", "შეფ", "მცხობელ"  # Food service
    ],
    "active": [
        "მძღოლ", "კურიერ", "ოფიცერ", "პოლიცი", "მწვრთნელ"
    ],
    "heavy": [
        "მშენებ", "ფერმ", "მეხანძრ", "სპორტსმენ", 
        "მეტყევე", "მეღვინე", "მჭედელ", "ტვირთმზიდ"  # Heavy labor (removed "მუშა" - false positive with "ვმუშაობ")
    ]
}

# Sensitive keywords (require confirmation)
SENSITIVE_KEYWORDS = [
    "ორსულ", "ფეხმძიმ",           # Pregnancy
    "დიაბეტ", "შაქრიან",          # Diabetes
    "გული", "არითმია",            # Heart conditions
    "ალერგია",                     # Allergies (may need explicit handling)
    "ტრავმა", "მოტეხილი", "დაზიანებ"  # Injuries
]

# Fact indicator phrases (semantic memory candidates)
FACT_INDICATORS = [
    r'მაქვს\s+(.{10,})',          # "მაქვს..."
    r'მტკივა\s+(.{5,})',          # "მტკივა..."
    r'არ\s+შემიძლია\s+(.{5,})',   # "არ შემიძლია..."
    r'პრობლემა.*?(.{10,})',       # "პრობლემა..."
    r'უყვარს\s+(.{5,})',          # "უყვარს..."
    r'არ\s+უყვარს\s+(.{5,})',     # "არ უყვარს..."
]

# =============================================================================
# NEGATION HANDLING (LLM Verification Triggers)
# =============================================================================

# Georgian negation patterns that require LLM verification
NEGATION_TRIGGERS = [
    'არ ვარ',      # "არ ვარ 20 წლის" = NOT 20 years old
    'კი არა',      # "20 კი არა, 30" = NOT 20, but 30
    'აღარ',        # "აღარ ვარ" = no longer
    'არა ვარ',     # Alternative negation
    'დავკარგე',    # "დავკარგე სამსახური" = lost job
    'წავედი',      # "წავედი ბანკიდან" = left bank
    'აღარა',       # Shorter negation form
    'ვიყავი',      # "ბანკირი ვიყავი" = was banker (past)
    'ადრე',        # "ადრე ვმუშაობდი" = used to work
]

# Context triggers (reference to others, not self)
CONTEXT_TRIGGERS = [
    'შვილ',        # Child ("ჩემი შვილია 10 წლის")
    'ძმა',         # Brother
    'და',          # Sister (also means "and" - context needed)
    'მშობ',        # Parent
    'მეგობ',       # Friend
]


# =============================================================================
# PROFILE EXTRACTOR
# =============================================================================

class ProfileExtractor:
    """
    Extracts user profile information from messages.
    
    Usage:
        extractor = ProfileExtractor()
        result = extractor.extract("40 წლის ვარ და ბანკში ვმუშაობ")
        # result.demographics = {"age": 40, "occupation": "ბანკში ვმუშაობ", "occupation_category": "sedentary"}
    """
    
    def __init__(self):
        # Compile patterns for efficiency
        self.age_patterns = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in AGE_PATTERNS]
        self.weight_patterns = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in WEIGHT_PATTERNS]
        self.height_patterns = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in HEIGHT_PATTERNS]
        self.fact_patterns = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in FACT_INDICATORS]
    
    def extract(self, message: str) -> ExtractionResult:
        """
        Extract all profile information from a message.
        
        Args:
            message: User message text
            
        Returns:
            ExtractionResult with extracted data
        """
        result = ExtractionResult()
        
        # Pre-process: Apply Latin → Georgian transliteration
        # This allows users to type e.g. "50 wlis var" instead of "50 წლის ვარ"
        processed_message = apply_transliteration(message)
        
        # 1. Extract structured data (use processed message for pattern matching)
        age = self._extract_age(processed_message)
        if age:
            result.demographics["age"] = age
            result.has_updates = True
        
        weight = self._extract_weight(processed_message)
        if weight:
            result.physical_stats["weight"] = weight
            result.has_updates = True
        
        height = self._extract_height(processed_message)
        if height:
            result.physical_stats["height"] = height
            result.has_updates = True
        
        # 2. Extract occupation
        occupation = self._extract_occupation(processed_message)
        if occupation:
            result.demographics["occupation"] = occupation["text"]
            result.demographics["occupation_category"] = occupation["category"]
            result.has_updates = True
        
        # 3. Extract potential facts (use original message to preserve user's words)
        facts = self._extract_potential_facts(message)
        if facts:
            result.potential_facts = facts
            result.has_updates = True
        
        # 4. Check for sensitive information (use original message)
        sensitive = self._check_sensitive(message)
        if sensitive:
            result.confirmations = sensitive
        
        return result
    
    def _extract_age(self, message: str) -> Optional[int]:
        """Extract age from message."""
        for pattern in self.age_patterns:
            match = pattern.search(message)
            if match:
                age = int(match.group(1))
                if 10 <= age <= 120:  # Reasonable age range
                    return age
        return None
    
    def _extract_weight(self, message: str) -> Optional[float]:
        """Extract weight (kg) from message.
        
        Smart negation handling: If message contains negation pattern like
        "90 კილო კი არ ვარ, 85 კილო ვარ", use the LAST valid match (85)
        instead of the first (90). This avoids LLM verification latency.
        """
        all_weights = []
        
        for pattern in self.weight_patterns:
            matches = pattern.finditer(message)
            for match in matches:
                weight = float(match.group(1))
                if 30 <= weight <= 300:  # Reasonable weight range
                    all_weights.append((weight, match.start()))
        
        if not all_weights:
            return None
        
        # Smart negation handling: use LAST weight when negation detected
        if has_negation(message) and len(all_weights) > 1:
            # Sort by position, take last one (the corrected value)
            all_weights.sort(key=lambda x: x[1])
            logger.info(f"🔄 Negation detected, using last weight: {all_weights[-1][0]} (rejected: {all_weights[0][0]})")
            return all_weights[-1][0]
        
        # Default: return first match
        return all_weights[0][0]
    
    def _extract_height(self, message: str) -> Optional[float]:
        """Extract height (cm) from message."""
        for pattern in self.height_patterns:
            match = pattern.search(message)
            if match:
                height = float(match.group(1))
                if 100 <= height <= 250:  # Reasonable height range
                    return height
        return None
    
    def _extract_occupation(self, message: str) -> Optional[Dict[str, str]]:
        """
        Extract occupation with conflict resolution.
        
        Uses "Negation-Aware Last Match Wins" algorithm:
        1. Find ALL occupation candidates with positions
        2. If negation detected near a candidate, skip it
        3. Return remaining candidate (or last by position if no negation)
        
        Examples:
            "ბანკში აღარ ვმუშაობ, მზარეული ვარ" → მზარეული ("ბანკში" skipped due to "აღარ")
            "მზარეული ვარ" → მზარეული (single candidate)
        
        Returns:
            {"text": "occupation context", "category": "sedentary|active|physical"}
        """
        message_lower = message.lower()
        candidates = []
        
        # 1. Find ALL candidates with positions
        for category, keywords in OCCUPATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    idx = message_lower.find(keyword)
                    # Extract surrounding context
                    start = max(0, idx - 20)
                    end = min(len(message), idx + len(keyword) + 20)
                    occupation_text = message[start:end].strip()
                    
                    candidates.append({
                        "keyword": keyword,
                        "position": idx,
                        "category": category,
                        "text": occupation_text
                    })
        
        if not candidates:
            return None
        
        # 2. Single candidate - return directly
        if len(candidates) == 1:
            cand = candidates[0]
            # Use keyword as occupation text (not full context to avoid negation words)
            return {"text": cand["keyword"], "category": cand["category"]}
        
        # 3. Multiple candidates - check for negation
        if has_negation(message):
            # Find earliest negation position
            negation_pos = -1
            for trigger in NEGATION_TRIGGERS:
                pos = message_lower.find(trigger)
                if pos != -1 and (negation_pos == -1 or pos < negation_pos):
                    negation_pos = pos
            
            # Filter out candidates near negation (within 30 chars)
            valid_candidates = [
                c for c in candidates 
                if abs(c["position"] - negation_pos) > 30
            ]
            
            if valid_candidates:
                # Return first valid (non-negated) candidate by position
                valid_candidates.sort(key=lambda x: x["position"])
                cand = valid_candidates[0]
                # Use keyword as occupation text (not context to avoid confusion)
                return {"text": cand["keyword"], "category": cand["category"]}
        
        # 4. No negation or all candidates valid - return LAST by position
        last_cand = max(candidates, key=lambda x: x["position"])
        # Use keyword as occupation text
        return {"text": last_cand["keyword"], "category": last_cand["category"]}
    
    def _extract_potential_facts(self, message: str) -> List[str]:
        """Extract potential semantic facts from message."""
        facts = []
        
        for pattern in self.fact_patterns:
            matches = pattern.findall(message)
            for match in matches:
                if len(match) >= 10:  # Minimum fact length
                    facts.append(match.strip())
        
        return facts
    
    def _check_sensitive(self, message: str) -> List[str]:
        """Check for sensitive information that needs confirmation."""
        confirmations = []
        message_lower = message.lower()
        
        for keyword in SENSITIVE_KEYWORDS:
            if keyword in message_lower:
                confirmations.append(
                    f"დავიმახსოვრე ინფორმაცია: \"{keyword}\" - ამის გათვალისწინებით მოგცემთ რჩევებს."
                )
        
        return confirmations
    
    def generate_confirmation(self, result: ExtractionResult) -> Optional[str]:
        """
        Generate confirmation message for extracted data.
        
        Used for explicit confirmation (user feedback recommendation).
        """
        parts = []
        
        if result.demographics.get("age"):
            parts.append(f"ასაკი: {result.demographics['age']} წელი")
        
        if result.physical_stats.get("weight"):
            parts.append(f"წონა: {result.physical_stats['weight']} კგ")
        
        if result.physical_stats.get("height"):
            parts.append(f"სიმაღლე: {result.physical_stats['height']} სმ")
        
        if result.demographics.get("occupation"):
            parts.append(f"პროფესია: {result.demographics['occupation']}")
        
        if parts:
            return "ინფორმაცია დავიმახსოვრე: " + ", ".join(parts)
        
        if result.confirmations:
            return result.confirmations[0]
        
        return None


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_long_term_fact(message: str) -> bool:
    """
    Heuristic check if a statement is a long-term fact.
    
    This is a simple heuristic; for production, use LLM classification.
    """
    # Temporary indicators (NOT long-term facts)
    temporary_keywords = [
        "დღეს", "ახლა", "ეხლა", "ამ წუთას", "ეს კვირა", 
        "გუშინ", "ზეგ", "ხვალ"
    ]
    
    message_lower = message.lower()
    
    # If contains temporary indicators, less likely to be long-term
    for keyword in temporary_keywords:
        if keyword in message_lower:
            return False
    
    # Long-term indicators
    long_term_keywords = [
        "ყოველთვის", "ხშირად", "ჩვეულებრივ", "წლებია", 
        "მუდმივად", "ჩემთვის", "მიყვარს", "არ მიყვარს"
    ]
    
    for keyword in long_term_keywords:
        if keyword in message_lower:
            return True
    
    # Default: check length (longer statements more likely to be facts)
    return len(message) > 30


def has_negation(text: str) -> bool:
    """
    Check if text contains Georgian negation patterns.
    
    Used to trigger LLM verification for extracted values.
    
    Args:
        text: User message text
        
    Returns:
        True if negation pattern detected
    """
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in NEGATION_TRIGGERS)


def has_context_reference(text: str) -> bool:
    """
    Check if text references another person (child, sibling, etc.).
    
    Used to avoid extracting someone else's data as user's data.
    
    Args:
        text: User message text
        
    Returns:
        True if context reference detected
    """
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in CONTEXT_TRIGGERS)


async def verify_fact_with_llm(
    text: str,
    field: str,
    extracted_value: Any,
    timeout: float = 0.5
) -> Optional[Any]:
    """
    Verify extracted value using Gemini Flash LLM.
    
    Called when negation is detected to disambiguate values.
    
    Args:
        text: Original user message
        field: Field name (age, weight, height)
        extracted_value: Value extracted by RegEx
        timeout: Max time for LLM call (default 500ms)
        
    Returns:
        Verified value if different, None if extraction should be rejected,
        or original value if LLM confirms
    """
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Import Gemini client
        from google import genai
        from config import settings
        
        client = genai.Client(api_key=settings.gemini_api_key)
        
        # Construct verification prompt (Georgian-aware)
        prompt = f"""ტექსტში მომხმარებლის {field} უნდა ამოვიღოთ.

ტექსტი: "{text}"
RegEx-მა ამოიღო: {extracted_value}

კითხვა: რა არის მომხმარებლის ნამდვილი {field}? 
- თუ {extracted_value} სწორია, დააბრუნე: {extracted_value}
- თუ სხვა მნიშვნელობაა სწორი, დააბრუნე ის რიცხვი
- თუ მომხმარებელი არ საუბრობს საკუთარ თავზე, დააბრუნე: null

მხოლოდ რიცხვი ან null დააბრუნე, არაფერი სხვა."""

        # Call Gemini Flash with timeout
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",  # Fast model for verification
                contents=prompt,
            ),
            timeout=timeout
        )
        
        result_text = response.text.strip().lower()
        
        # Parse response
        if result_text == 'null' or result_text == 'none':
            logger.info(f"🔍 LLM rejected extraction: {field}={extracted_value} (not user's data)")
            return None
        
        try:
            verified_value = int(result_text) if field == 'age' else float(result_text)
            if verified_value != extracted_value:
                logger.info(f"🔍 LLM corrected: {field}={verified_value} (was {extracted_value})")
            else:
                logger.debug(f"🔍 LLM confirmed: {field}={extracted_value}")
            return verified_value
        except ValueError:
            # LLM returned non-numeric, trust original extraction
            logger.warning(f"⚠️ LLM returned invalid value '{result_text}', using RegEx result")
            return extracted_value
            
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ LLM verification timeout ({timeout}s), using RegEx result")
        return extracted_value
    except Exception as e:
        logger.error(f"❌ LLM verification error: {e}, using RegEx result")
        return extracted_value
