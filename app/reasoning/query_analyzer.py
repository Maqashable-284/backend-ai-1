"""
Query Analyzer - Extract constraints, intent, myths, and goals from user messages
Scoop AI Orchestration Layer v1.0
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class QueryAnalysis:
    """Structured analysis of user query"""
    # Constraints
    budget: Optional[float] = None
    dietary_restrictions: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    duration_months: Optional[int] = None

    # Intent
    intent: str = "general"  # product_search, myth_question, greeting, faq, medical
    complexity: str = "simple"  # simple, complex

    # Issues to address
    myths_detected: List[str] = field(default_factory=list)
    unrealistic_goals: List[str] = field(default_factory=list)
    medical_concerns: List[str] = field(default_factory=list)
    safety_concerns: List[str] = field(default_factory=list)

    # Products
    products_requested: List[str] = field(default_factory=list)

    # User profile
    is_beginner: bool = False
    goal_type: Optional[str] = None  # weight_loss, muscle_gain, endurance, recovery


# =============================================================================
# BUDGET EXTRACTION PATTERNS
# =============================================================================
BUDGET_PATTERNS = [
    (r'(\d+)\s*(?:ლარ|₾|lari)', 'direct'),           # "150 ლარი", "150₾"
    (r'ბიუჯეტ\w*\s*(\d+)', 'direct'),                # "ბიუჯეტი 150"
    (r'(\d+)\s*ბიუჯეტ', 'direct'),                   # "150 ბიუჯეტი"
    (r'სტიპენდია\s*(\d+)', 'implicit'),              # "სტიპენდია 100"
    (r'ხელფას\w*\s*(\d+)', 'implicit'),              # "ხელფასი 500"
    (r'მაქვს\s*(?:სულ\s*)?(\d+)', 'direct'),         # "მაქვს სულ 150"
    (r'მაქს(?:იმუმ)?\s*(\d+)', 'direct'),            # "მაქსიმუმ 200"
    (r'(\d+)\s*მაქს', 'direct'),                      # "200 მაქს"
    (r'არაუმეტეს\s*(\d+)', 'direct'),                # "არაუმეტეს 150"
    (r'პენსია\s*(\d+)', 'implicit'),                 # "პენსია 400"
    (r'(\d+)-(\d+)\s*(?:ლარ|₾)', 'range'),           # "100-150 ლარი" (takes min)
]

# =============================================================================
# MYTH DETECTION PATTERNS
# =============================================================================
MYTH_PATTERNS = {
    'protein_chemical': [
        r'პროტეინ\w*\s*(?:ქიმია|სინთეტიკ|ხელოვნურ|არაბუნებრივ)',
        r'პროტეინ\w*\s*(?:არის|არის\s*ეს)\s*ქიმია',
        r'(?:ქიმია|სინთეტიკ)\w*\s*პროტეინ',
        r'protein\s*(?:chemical|synthetic|artificial|unnatural)',
        r'whey\s*(?:chemical|synthetic)',
        r'პროტეინი\s*ბუნებრივი\s*არ\s*არის',
    ],
    'soy_estrogen': [
        r'სოი\w*\s*(?:ესტროგენ|ქალ|ჰორმონ|აქალებ)',
        r'სოი\w*.*(?:კაც|მამაკაც).*(?:აქალებ|ქალ)',
        r'soy\s*(?:estrogen|feminine|hormone)',
        r'სოია\s*კაცს\s*აქალებს',
        r'სოი\w*.*ესტროგენ\w*',  # "სოიოს...ესტროგენს" - any soy + estrogen combo
        r'სოი\w*.*(?:დავემსგავს|გავხდები|ვიქცევი).*ქალ',  # "სოიოს...ქალს დავემსგავსები"
        r'სოი\w*.*ქალ\w*\s*(?:დავემსგავს|გავხდები|ვიქცევი)',  # "ქალს დავემსგავსები"
        r'ესტროგენ\w*.*სოი\w*',  # reverse order: "ესტროგენი სოიოდან"
    ],
    'creatine_steroid': [
        r'კრეატინ\w*\s*(?:სტეროიდ|დოპინგ|არალეგალ)',
        r'კრეატინ\w*\s*კანონიერ',
        r'creatine\s*(?:steroid|doping|illegal)',
    ],
    'protein_kidney': [
        r'პროტეინ\w*\s*(?:თირკმელ|კიდნი|kidney)',
        r'პროტეინ\w*.*(?:აზიანებს|დააზიანებს).*თირკმელ',
        r'protein\s*(?:kidney|renal)\s*(?:damage|harm)',
    ],
}

# =============================================================================
# UNREALISTIC GOAL PATTERNS
# =============================================================================
UNREALISTIC_PATTERNS = {
    'rapid_muscle': [
        r'(\d+)\s*კგ\s*(?:კუნთ|მასა)\w*\s*(\d+)\s*(?:თვე|კვირა)',
        r'(\d+)\s*(?:თვე|კვირა)\w*\s*(\d+)\s*კგ\s*(?:კუნთ|მასა)',
    ],
    'impossible_price': [
        r'100\s*%\s*(?:ცილა|პროტეინ)\w*\s*(\d+)\s*(?:ლარ|₾)',
        r'იაფ\w*\s*100\s*%\s*(?:ცილა|პროტეინ)',
        r'100\s*%\s*(?:ცილა|პროტეინ)\w*.*?(\d+)\s*(?:ლარ|₾)',  # "100% ცილის ... 20 ლარად"
        r'100\s*%\s*ცილ\w*.*პროტეინ\w*.*?(\d+)\s*(?:ლარ|₾)',  # "100% ცილის პროტეინი 20 ლარად"
    ],
    'rapid_weight_loss': [
        r'(\d+)\s*კგ\s*(?:დაკლება|წონა)\w*\s*(\d+)\s*(?:კვირა|დღე)',
    ],
}

# =============================================================================
# MEDICAL RISK PATTERNS
# =============================================================================
MEDICAL_RISK_PATTERNS = {
    'ssri_interaction': [
        r'(?:ანტიდეპრესანტ|ssri|სეროტონინ)',
        r'(?:antidepressant|prozac|zoloft|lexapro|sertraline|escitalopram)',
    ],
    'kidney_concern': [
        r'(?:კრეატინინ|თირკმელ\w*\s*პრობლემ)',
        r'(?:kidney\s*(?:disease|problem)|renal|creatinine\s*high)',
    ],
    'liver_concern': [
        r'(?:ღვიძლ\w*\s*პრობლემ|ღვიძლის\s*დაავადება)',
        r'(?:liver\s*(?:disease|problem)|hepat)',
    ],
    'heart_concern': [
        r'(?:გულ\w*\s*პრობლემ|არითმია|გულის\s*დაავადება)',
        r'(?:heart\s*(?:disease|problem)|cardiac|arrhythmia)',
    ],
    'blood_pressure': [
        r'(?:წნევა\s*მაღალ|ჰიპერტენზია)',
        r'(?:high\s*(?:blood\s*)?pressure|hypertension)',
    ],
    'diabetes': [
        r'(?:დიაბეტ|შაქრიან\w*\s*დიაბეტ)',
        r'(?:diabetes|blood\s*sugar|diabetic)',
    ],
    'pregnancy': [
        r'(?:ორსულ|მეძუძური|ბავშვს\s*ვაძუძებ)',
        r'(?:pregnant|breastfeed|nursing)',
    ],
    'thyroid': [
        r'(?:ფარისებრ\w*\s*ჯირკვ)',
        r'(?:thyroid)',
    ],
}

# =============================================================================
# SAFETY CONCERN PATTERNS
# =============================================================================
SAFETY_CONCERN_PATTERNS = {
    'caffeine_overuse': [
        r'(\d+)\s*(?:ჯერ|times).*(?:პრე-ვორკაუთ|preworkout|კოფეინ)',
        r'(?:აღარ\s*მშველის|არ\s*მუშაობს|tolerance)',
        r'დღეში\s*(\d+).*(?:პრე-ვორკაუთ|preworkout)',
        r'უფრო\s*ძლიერი.*(?:პრე-ვორკაუთ|preworkout)',
    ],
    'eating_disorder_risk': [
        r'(?:არ\s*მიჭამია|არ\s*ვჭამ|not\s*eating)',
        r'მხოლოდ.*(?:ცხიმისმწველ|fat\s*burner)',
        r'(?:ანორექსია|ბულიმია|anorexia|bulimia)',
    ],
    'overdose_risk': [
        r'(?:ორმაგი?\s*დოზ|double\s*dose)',
        r'(?:მეტი\s*მივიღო|take\s*more)',
    ],
}

# =============================================================================
# SYMPTOM PATTERNS
# =============================================================================
SYMPTOM_PATTERNS = {
    'paresthesia': [
        r'(?:მექავება|ჩხვლეტ|tingling|itching)',
        r'(?:სახე|face).*(?:მექავება|ჩხვლეტ|tingling)',
        r'(?:კანი|skin).*(?:მექავება|tingling)',
    ],
    'general_discomfort': [
        r'(?:ცუდად|გულისრევა|nausea|sick|თავბრუ)',
        r'(?:მტკივა|ტკივილი|pain|hurts)',
    ],
    'digestive': [
        r'(?:მუცელი\s*მტკივა|stomach\s*(?:pain|ache)|შებერილობა|bloating)',
    ],
}

# =============================================================================
# PRODUCT KEYWORDS
# =============================================================================
PRODUCT_KEYWORDS = {
    'protein': ['პროტეინ', 'ცილა', 'whey', 'protein', 'casein', 'კაზეინ'],
    'creatine': ['კრეატინ', 'creatine'],
    'omega': ['ომეგა', 'omega', 'თევზის ცხიმი', 'fish oil'],
    'bcaa': ['bcaa', 'ამინო', 'amino', 'eaa'],
    'vitamin': ['ვიტამინ', 'vitamin', 'მულტივიტამინ', 'multivitamin'],
    'preworkout': ['პრე-ვორკაუთ', 'პრევორკაუთ', 'preworkout', 'pre-workout', 'ენერგეტიკ'],
    'fat_burner': ['ცხიმისმწველ', 'fat burner', 'თერმოგენიკ', 'thermogenic'],
    'mass_gainer': ['გეინერ', 'gainer', 'მას გეინერ', 'mass'],
    'glutamine': ['გლუტამინ', 'glutamine'],
    'collagen': ['კოლაგენ', 'collagen'],
}

# =============================================================================
# GOAL PATTERNS
# =============================================================================
GOAL_PATTERNS = {
    'weight_loss': [r'(?:წონა.*დაკლება|დიეტა|გამოშრობა|წონის.*დაკლება|slim|cut|დაკლება)'],
    'muscle_gain': [r'(?:კუნთ.*მომატება|მასა|bulk|muscle.*gain|კუნთები)'],
    'maintenance': [r'(?:შენარჩუნება|maintain|მაინტენანს)'],
    'endurance': [r'(?:გამძლეობა|endurance|სირბილ|მარათონ|კარდიო)'],
    'recovery': [r'(?:აღდგენ|recovery|ტკივილ.*კუნთ|კუნთების.*აღდგენა)'],
}

# =============================================================================
# BEGINNER DETECTION
# =============================================================================
BEGINNER_PATTERNS = [
    r'პირველად.*(?:დარბაზ|ვარჯიშ|gym|სპორტდარბაზ)',
    r'(?:ახალბედა|beginner|დამწყები)',
    r'არასდროს.*(?:ვარჯიშ|დანამატ)',
    r'ახლა\s*დავიწყე.*(?:ვარჯიშ|დარბაზ)',
    r'(?:რა\s*დავიწყო|საიდან\s*დავიწყო)',
]

# =============================================================================
# TIME/DURATION PATTERNS
# =============================================================================
TIME_DURATION_PATTERNS = [
    (r'(\d+)\s*(?:თვე|თვის|month)', 'months'),
    (r'(\d+)\s*(?:კვირა|week)', 'weeks'),
    (r'(\d+)\s*(?:წელ|year)', 'years'),
    (r'ეყოფა\s*(\d+)\s*(?:თვე|კვირა)', 'duration'),
]

# =============================================================================
# EXCLUSION PATTERNS
# =============================================================================
EXCLUSION_KEYWORDS = [
    (r'არ\s*მინდა\s*(\w+)', 'exclude'),
    (r'(\w+)\s*გარეშე', 'exclude'),
    (r'გამოვრიცხო\s*(\w+)', 'exclude'),
    (r'without\s*(\w+)', 'exclude'),
    (r'არ\s*შეიცავდეს\s*(\w+)', 'exclude'),
    (r'თავი\s*აარიდოს\s*(\w+)', 'exclude'),
]

# Common exclusion items
EXCLUSION_ITEMS = {
    'შაქარ': 'sugar',
    'sugar': 'sugar',
    'კოფეინ': 'caffeine',
    'caffeine': 'caffeine',
    'ლაქტოზ': 'lactose',
    'lactose': 'lactose',
    'გლუტენ': 'gluten',
    'gluten': 'gluten',
    'სოი': 'soy',
    'soy': 'soy',
}


def analyze_query(message: str, history: List[Dict] = None) -> QueryAnalysis:
    """
    Analyze user query for constraints, intent, myths, and goals.

    Args:
        message: Current user message
        history: Previous conversation (for context carryover)

    Returns:
        QueryAnalysis with all extracted information
    """
    analysis = QueryAnalysis()
    message_lower = message.lower()

    # Combine with recent history for context
    full_context = message_lower
    if history:
        recent = history[-4:]  # Last 2 exchanges
        for h in recent:
            # Handle both dict format and SDK's Pydantic objects
            role = h.get('role') if isinstance(h, dict) else getattr(h, 'role', None)
            if role == 'user':
                parts = h.get('parts', []) if isinstance(h, dict) else getattr(h, 'parts', [])
                for part in parts:
                    if isinstance(part, dict) and 'text' in part:
                        full_context += " " + part['text'].lower()
                    elif isinstance(part, str):
                        full_context += " " + part.lower()
                    elif hasattr(part, 'text') and part.text is not None:
                        # Handle SDK Part object
                        full_context += " " + part.text.lower()

    # === EXTRACT BUDGET ===
    for pattern, budget_type in BUDGET_PATTERNS:
        match = re.search(pattern, full_context)
        if match:
            if budget_type == 'range':
                analysis.budget = float(match.group(1))  # Take minimum
            else:
                analysis.budget = float(match.group(1))
            break

    # === DETECT DIETARY RESTRICTIONS ===
    if any(word in full_context for word in ['ლაქტოზ', 'lactose', 'რძის აუტანლობა']):
        analysis.dietary_restrictions.append('lactose-free')
    if any(word in full_context for word in ['ვეგან', 'vegan', 'მცენარეულ']):
        analysis.dietary_restrictions.append('vegan')
    if any(word in full_context for word in ['გლუტენ', 'gluten']):
        analysis.dietary_restrictions.append('gluten-free')

    # === DETECT EXCLUSIONS ===
    for pattern, _ in EXCLUSION_KEYWORDS:
        matches = re.finditer(pattern, full_context, re.IGNORECASE)
        for match in matches:
            excluded_item = match.group(1).lower()
            for key, value in EXCLUSION_ITEMS.items():
                if key in excluded_item:
                    if value not in analysis.exclusions:
                        analysis.exclusions.append(value)

    # === DETECT MYTHS ===
    for myth_id, patterns in MYTH_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, full_context, re.IGNORECASE):
                if myth_id not in analysis.myths_detected:
                    analysis.myths_detected.append(myth_id)
                break

    # === DETECT UNREALISTIC GOALS ===
    for goal_id, patterns in UNREALISTIC_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, full_context, re.IGNORECASE)
            if match:
                if goal_id == 'rapid_muscle':
                    try:
                        kg = int(match.group(1))
                        months = int(match.group(2))
                        if kg / max(months, 1) > 2:  # >2kg/month is unrealistic
                            analysis.unrealistic_goals.append(f"{goal_id}:{kg}kg/{months}mo")
                    except (ValueError, IndexError):
                        analysis.unrealistic_goals.append(goal_id)
                elif goal_id == 'rapid_weight_loss':
                    try:
                        kg = int(match.group(1))
                        weeks = int(match.group(2))
                        if kg / max(weeks, 1) > 1:  # >1kg/week is unhealthy
                            analysis.unrealistic_goals.append(f"{goal_id}:{kg}kg/{weeks}wk")
                    except (ValueError, IndexError):
                        analysis.unrealistic_goals.append(goal_id)
                else:
                    analysis.unrealistic_goals.append(goal_id)

    # === DETECT MEDICAL CONCERNS ===
    for concern_id, patterns in MEDICAL_RISK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, full_context, re.IGNORECASE):
                if concern_id not in analysis.medical_concerns:
                    analysis.medical_concerns.append(concern_id)
                break

    # === DETECT SAFETY CONCERNS ===
    for concern_id, patterns in SAFETY_CONCERN_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, full_context, re.IGNORECASE):
                if concern_id not in analysis.safety_concerns:
                    analysis.safety_concerns.append(concern_id)
                break

    # === DETECT SYMPTOMS ===
    for symptom_id, patterns in SYMPTOM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, full_context, re.IGNORECASE):
                if symptom_id not in analysis.medical_concerns:
                    analysis.medical_concerns.append(f"symptom:{symptom_id}")
                break

    # === DETECT PRODUCTS REQUESTED ===
    for product_id, keywords in PRODUCT_KEYWORDS.items():
        if any(kw in full_context for kw in keywords):
            if product_id not in analysis.products_requested:
                analysis.products_requested.append(product_id)

    # === DETECT BEGINNER STATUS ===
    for pattern in BEGINNER_PATTERNS:
        if re.search(pattern, full_context, re.IGNORECASE):
            analysis.is_beginner = True
            break

    # === DETECT GOAL TYPE ===
    for goal_type, patterns in GOAL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, full_context, re.IGNORECASE):
                analysis.goal_type = goal_type
                break
        if analysis.goal_type:
            break

    # === DETECT DURATION ===
    for pattern, duration_type in TIME_DURATION_PATTERNS:
        match = re.search(pattern, full_context)
        if match:
            value = int(match.group(1))
            if duration_type == 'months' or duration_type == 'duration':
                analysis.duration_months = value
            elif duration_type == 'weeks':
                analysis.duration_months = max(1, value // 4)
            elif duration_type == 'years':
                analysis.duration_months = value * 12
            break

    # === DETERMINE COMPLEXITY ===
    complexity_score = 0
    if analysis.budget:
        complexity_score += 1
    if analysis.dietary_restrictions:
        complexity_score += 1
    if analysis.exclusions:
        complexity_score += 1
    if analysis.myths_detected:
        complexity_score += 2
    if analysis.unrealistic_goals:
        complexity_score += 2
    if analysis.medical_concerns:
        complexity_score += 2
    if analysis.safety_concerns:
        complexity_score += 2
    if len(analysis.products_requested) > 2:
        complexity_score += 1
    if analysis.is_beginner and len(analysis.products_requested) > 1:
        complexity_score += 1  # Beginner asking for many products = needs guidance

    analysis.complexity = "complex" if complexity_score >= 2 else "simple"

    # === DETERMINE INTENT ===
    if analysis.medical_concerns or analysis.safety_concerns:
        analysis.intent = "medical"
    elif analysis.myths_detected:
        analysis.intent = "myth_question"
    elif analysis.products_requested:
        analysis.intent = "product_search"
    elif any(word in message_lower for word in ['გამარჯობა', 'სალამი', 'hello', 'hi']):
        analysis.intent = "greeting"
    else:
        analysis.intent = "general"

    return analysis
