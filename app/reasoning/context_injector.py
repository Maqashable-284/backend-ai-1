"""
Context Injector - Enhance user message with analysis results
Scoop AI Orchestration Layer v1.0
"""
import logging
from typing import Optional, Dict, Any

from app.reasoning.query_analyzer import QueryAnalysis
from app.reasoning.constraint_search import ConstrainedSearchResult

logger = logging.getLogger(__name__)

# =============================================================================
# MYTH DEBUNKING RESPONSES (Georgian)
# =============================================================================
MYTH_RESPONSES = {
    'protein_chemical': "პროტეინი არის ბუნებრივი ცილა რძიდან/მცენარეებიდან - იგივე რაც ხორცში ან კვერცხში. არანაირი ქიმია.",
    'soy_estrogen': "ფიტოესტროგენი ≠ ადამიანის ესტროგენი. 100+ კვლევა ადასტურებს - სოიო არ ცვლის ტესტოსტერონს კაცებში.",
    'creatine_steroid': "კრეატინი ბუნებრივად გვხვდება ხორცში. WADA დამტკიცებული, არ არის დოპინგი და სრულიად ლეგალურია.",
    'protein_kidney': "ჯანმრთელ ადამიანში პროტეინი უსაფრთხოა. თირკმელების პრობლემა მხოლოდ უკვე არსებული დაავადებისას.",
}

# =============================================================================
# UNREALISTIC GOAL CORRECTIONS (Georgian)
# =============================================================================
GOAL_CORRECTIONS = {
    'rapid_muscle': "ბუნებრივად შესაძლებელია თვეში 0.5-1კგ სუფთა კუნთის მომატება. {kg}კგ-ისთვის საჭიროა ~{months} თვე.",
    'impossible_price': "100% ცილა ფიზიკურად შეუძლებელია - საუკეთესო იზოლატებიც 90-95%-ია. ხარისხიანი პროტეინი 80₾-დან იწყება.",
    'rapid_weight_loss': "ჯანსაღი წონის დაკლება კვირაში 0.5-1კგ-ია. სწრაფი დაკლება კუნთის დაკარგვას იწვევს.",
}

# =============================================================================
# MEDICAL WARNING TEMPLATES (Georgian)
# =============================================================================
MEDICAL_WARNINGS = {
    'ssri_interaction': "SSRI/ანტიდეპრესანტი + კოფეინიანი პრე-ვორკაუთი = სეროტონინის სინდრომის რისკი. ექიმთან კონსულტაცია სავალდებულოა!",
    'kidney_concern': "თირკმელების პრობლემისას კრეატინის მიღება ექიმის რეკომენდაციით. ჯანმრთელ ადამიანში უსაფრთხოა.",
    'liver_concern': "ღვიძლის პრობლემისას ზოგიერთი დანამატი შეზღუდულია. ექიმთან კონსულტაცია რეკომენდებულია.",
    'heart_concern': "გულის პრობლემისას კოფეინიანი პროდუქტები (პრე-ვორკაუთი) კონტრინდიცირებულია!",
    'blood_pressure': "მაღალი წნევისას კოფეინიანი პროდუქტები სიფრთხილით. ექიმთან კონსულტაცია.",
    'diabetes': "დიაბეტისას უშაქრო პროდუქტები უპირატესია. გეინერები და შაქრიანი პროდუქტები არ არის რეკომენდებული.",
    'pregnancy': "ორსულობისას/ძუძუთი კვებისას: fat burners, თერმოგენიკები, კოფეინიანი პრე-ვორკაუთები აკრძალულია!",
    'thyroid': "ფარისებრი ჯირკვლის პრობლემისას იოდიანი დანამატები ექიმის კონსულტაციით.",
}

# =============================================================================
# SAFETY CONCERN RESPONSES (Georgian)
# =============================================================================
SAFETY_RESPONSES = {
    'caffeine_overuse': "კოფეინის tolerance ნიშანია რომ ორგანიზმს შესვენება სჭირდება. 1-2 კვირით შეაჩერე პრე-ვორკაუთი.",
    'eating_disorder_risk': "ცხიმისმწველი საკვების გარეშე არ მუშაობს! ჯერ კალორიული დეფიციტი და სწორი კვება, შემდეგ დანამატები.",
    'overdose_risk': "ორმაგი დოზა არ ნიშნავს ორმაგ ეფექტს - მხოლოდ გვერდით ეფექტებს ზრდის.",
}

# =============================================================================
# SYMPTOM EXPLANATIONS (Georgian)
# =============================================================================
SYMPTOM_EXPLANATIONS = {
    'symptom:paresthesia': "სახის/კანის ჩხვლეტა პრე-ვორკაუთის შემდეგ = ბეტა-ალანინის პარესთეზია. ეს ნორმალურია და უვნებელია!",
    'symptom:general_discomfort': "თუ ცუდად ხარ დანამატის მიღების შემდეგ, შეაჩერე მოხმარება და ექიმს მიმართე.",
    'symptom:digestive': "საჭმლის მონელების პრობლემა? სცადე დანამატი საკვებთან ერთად ან დოზა შეამცირე.",
}

# =============================================================================
# BEGINNER WARNING (Georgian)
# =============================================================================
BEGINNER_WARNING = """დამწყებისთვის ბევრი დანამატი ერთდროულად არ არის საჭირო!
დაიწყე მხოლოდ: პროტეინი + (ოპციურად) მულტივიტამინი.
3-6 თვის შემდეგ შეგიძლია კრეატინის დამატება."""


def _build_profile_block(profile: Dict[str, Any]) -> str:
    """
    Build [USER_PROFILE] block from stored user data.
    
    Args:
        profile: User document from UserStore.get_user()
        
    Returns:
        Formatted profile block or empty string if no data
    """
    if not profile:
        return ""
    
    demographics = profile.get("demographics", {})
    stats = profile.get("physical_stats", {})
    
    parts = []
    
    if demographics.get("age"):
        parts.append(f"👤 ასაკი: {demographics['age']} წ")
    if stats.get("weight"):
        parts.append(f"⚖️ წონა: {stats['weight']} კგ")
    if stats.get("height"):
        parts.append(f"📏 სიმაღლე: {stats['height']} სმ")
    if demographics.get("occupation_category"):
        category = demographics['occupation_category']
        parts.append(f"💼 საქმიანობა: {category}")
    
    if parts:
        return "[USER_PROFILE]\n" + "\n".join(parts) + "\n[/USER_PROFILE]\n\n"
    return ""


def inject_context(
    original_message: str,
    analysis: QueryAnalysis,
    search_result: Optional[ConstrainedSearchResult] = None,
    user_profile: Optional[Dict[str, Any]] = None
) -> str:
    """
    Inject analysis context into user message for Gemini.

    This provides structured information so Gemini doesn't have to
    figure out constraints, myths, etc. on its own.

    Args:
        original_message: Original user message
        analysis: Query analysis with constraints
        search_result: Optional search results with products

    Returns:
        Enhanced message with [ANALYSIS] block prepended
    """
    context_parts = []

    # === BUDGET CONTEXT ===
    if analysis.budget:
        status = ""
        if search_result:
            if search_result.budget_status == "under":
                status = f"✓ ჯამი {search_result.total_price:.0f}₾ ≤ {analysis.budget}₾"
            elif search_result.budget_status == "under_after_drops":
                dropped = ", ".join(search_result.dropped_products)
                status = f"⚠️ ბიუჯეტში ჩასატევად გამოვტოვე: {dropped}"
            elif search_result.budget_status == "over":
                status = f"✗ ჯამი {search_result.total_price:.0f}₾ > {analysis.budget}₾"
        context_parts.append(f"💰 ბიუჯეტი: {analysis.budget}₾ {status}")

    # === DIETARY CONTEXT ===
    if analysis.dietary_restrictions:
        restrictions = ", ".join(analysis.dietary_restrictions)
        context_parts.append(f"🥗 დიეტა: {restrictions}")

    # === EXCLUSIONS CONTEXT ===
    if analysis.exclusions:
        exclusions = ", ".join(analysis.exclusions)
        context_parts.append(f"🚫 გამორიცხულია: {exclusions}")

    # === DURATION CONTEXT ===
    if analysis.duration_months:
        context_parts.append(f"📅 მარაგი: {analysis.duration_months} თვე")

    # === GOAL CONTEXT ===
    if analysis.goal_type:
        goal_names = {
            'weight_loss': 'წონის დაკლება',
            'muscle_gain': 'კუნთის მომატება',
            'maintenance': 'შენარჩუნება',
            'endurance': 'გამძლეობა',
            'recovery': 'აღდგენა',
        }
        context_parts.append(f"🎯 მიზანი: {goal_names.get(analysis.goal_type, analysis.goal_type)}")

    # === MYTH DEBUNKING CONTEXT ===
    if analysis.myths_detected:
        context_parts.append("🔬 მითები გასაქარწყლებელი:")
        for myth in analysis.myths_detected:
            if myth in MYTH_RESPONSES:
                context_parts.append(f"  • {MYTH_RESPONSES[myth]}")

    # === UNREALISTIC GOALS CONTEXT ===
    if analysis.unrealistic_goals:
        context_parts.append("⚠️ რეალისტური კორექცია საჭირო:")
        for goal in analysis.unrealistic_goals:
            goal_type = goal.split(':')[0]
            if goal_type in GOAL_CORRECTIONS:
                correction = GOAL_CORRECTIONS[goal_type]
                # Parse numbers if available
                if ':' in goal:
                    params = goal.split(':')[1]
                    if 'kg' in params:
                        try:
                            kg = int(params.split('kg')[0])
                            months = max(kg, kg * 2)  # Realistic timeline
                            correction = correction.format(kg=kg, months=f"{kg}-{months}")
                        except (ValueError, IndexError):
                            pass
                context_parts.append(f"  • {correction}")

    # === MEDICAL CONCERNS CONTEXT ===
    if analysis.medical_concerns:
        context_parts.append("🏥 სამედიცინო გაფრთხილება:")
        for concern in analysis.medical_concerns:
            if concern in MEDICAL_WARNINGS:
                context_parts.append(f"  • {MEDICAL_WARNINGS[concern]}")
            elif concern in SYMPTOM_EXPLANATIONS:
                context_parts.append(f"  • {SYMPTOM_EXPLANATIONS[concern]}")
            else:
                # Generic medical redirect
                context_parts.append("  • ექიმთან კონსულტაცია რეკომენდებულია")

    # === SAFETY CONCERNS CONTEXT ===
    if analysis.safety_concerns:
        context_parts.append("⚠️ უსაფრთხოების გაფრთხილება:")
        for concern in analysis.safety_concerns:
            if concern in SAFETY_RESPONSES:
                context_parts.append(f"  • {SAFETY_RESPONSES[concern]}")

    # === BEGINNER WARNING ===
    if analysis.is_beginner and len(analysis.products_requested) > 2:
        context_parts.append(f"👶 ახალბედას რჩევა:\n{BEGINNER_WARNING}")

    # === SEARCH RESULT WARNINGS ===
    if search_result and search_result.warnings:
        if 'beginner_overload' in search_result.warnings:
            if "👶 ახალბედას რჩევა:" not in "\n".join(context_parts):
                context_parts.append(f"👶 ახალბედას რჩევა:\n{BEGINNER_WARNING}")

    # === PRODUCTS FOUND CONTEXT ===
    if search_result and search_result.products:
        context_parts.append(f"📦 ნაპოვნი პროდუქტები ({len(search_result.products)}):")
        for p in search_result.products:
            category = p.get('_category', '')
            name = p.get('name', 'Unknown')
            price = p.get('price', 0)
            context_parts.append(f"  • {name} - {price}₾ ({category})")

        if search_result.total_price > 0:
            context_parts.append(f"  💵 ჯამი: {search_result.total_price:.0f}₾")

    # === BUILD ENHANCED MESSAGE ===
    # Build profile block (if user data exists)
    profile_block = _build_profile_block(user_profile) if user_profile else ""
    
    if context_parts:
        context_block = "[ANALYSIS]\n" + "\n".join(context_parts) + "\n[/ANALYSIS]\n\n"
        enhanced = profile_block + context_block + original_message
        logger.info(f"📝 Context injected: {len(context_parts)} sections, profile={'yes' if profile_block else 'no'}, {len(enhanced)} chars")
        return enhanced
    
    # Even if no analysis, inject profile if available
    if profile_block:
        return profile_block + original_message

    return original_message
