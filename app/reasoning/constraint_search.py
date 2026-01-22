"""
Constraint-Aware Product Search
Respects budget, dietary restrictions, and prioritizes products
Scoop AI Orchestration Layer v1.0
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from app.reasoning.query_analyzer import QueryAnalysis

logger = logging.getLogger(__name__)

# =============================================================================
# PRODUCT PRIORITY (higher = more essential for beginners/general)
# =============================================================================
PRODUCT_PRIORITY = {
    'protein': 100,      # Most essential
    'creatine': 80,      # Very effective, cheap
    'vitamin': 60,       # Supporting
    'omega': 50,         # Supporting
    'collagen': 40,      # Niche
    'bcaa': 30,          # Optional (covered by protein)
    'glutamine': 20,     # Optional
    'mass_gainer': 15,   # Specific use case
    'fat_burner': 10,    # Luxury / risky
    'preworkout': 10,    # Luxury
}


@dataclass
class ConstrainedSearchResult:
    """Results from constraint-aware search"""
    products: List[Dict] = field(default_factory=list)
    total_price: float = 0.0
    budget: Optional[float] = None
    budget_status: str = "no_budget"  # "under", "over", "under_after_drops", "no_budget"
    dropped_products: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def search_with_constraints(
    analysis: QueryAnalysis,
    max_per_category: int = 2
) -> ConstrainedSearchResult:
    """
    Search products while respecting constraints.

    1. Search each requested product category
    2. Filter by dietary restrictions
    3. Accumulate prices
    4. If over budget, drop lowest priority items

    Args:
        analysis: Query analysis with constraints
        max_per_category: Max products per category

    Returns:
        ConstrainedSearchResult with validated products
    """
    # Import here to avoid circular imports
    from app.tools.user_tools import search_products

    result = ConstrainedSearchResult(budget=analysis.budget)
    all_products = []

    # Sort products by priority (search high priority first)
    sorted_products = sorted(
        analysis.products_requested,
        key=lambda p: PRODUCT_PRIORITY.get(p, 50),
        reverse=True
    )

    logger.info(f"🔍 Constraint search: products={sorted_products}, budget={analysis.budget}, "
                f"dietary={analysis.dietary_restrictions}")

    # Search each product category
    for product_type in sorted_products:
        # Calculate max_price for this category if budget exists
        max_price = None
        if analysis.budget and len(sorted_products) > 0:
            # Allocate budget proportionally by priority
            total_priority = sum(PRODUCT_PRIORITY.get(p, 50) for p in sorted_products)
            product_priority = PRODUCT_PRIORITY.get(product_type, 50)
            # Give each product its proportional share + 20% buffer
            max_price = analysis.budget * (product_priority / total_priority) * 1.5

        # Map product_type to search query
        query_map = {
            'protein': 'პროტეინ',
            'creatine': 'კრეატინ',
            'vitamin': 'ვიტამინ',
            'omega': 'ომეგა',
            'bcaa': 'bcaa',
            'preworkout': 'პრევორკაუთ',
            'fat_burner': 'ცხიმისმწველ',
            'mass_gainer': 'გეინერ',
            'glutamine': 'გლუტამინ',
            'collagen': 'კოლაგენ',
        }
        search_query = query_map.get(product_type, product_type)

        # Search
        try:
            search_result = search_products(
                query=search_query,
                max_price=max_price,
                in_stock_only=True
            )
            products = search_result.get('products', [])
            logger.info(f"  📦 {product_type}: found {len(products)} products (max_price={max_price})")
        except Exception as e:
            logger.error(f"  ❌ {product_type}: search error: {e}")
            products = []

        # Filter by dietary restrictions
        if 'lactose-free' in analysis.dietary_restrictions:
            products = [p for p in products if is_lactose_free(p)]
            logger.info(f"    → After lactose filter: {len(products)}")

        if 'vegan' in analysis.dietary_restrictions:
            products = [p for p in products if is_vegan(p)]
            logger.info(f"    → After vegan filter: {len(products)}")

        if 'gluten-free' in analysis.dietary_restrictions:
            products = [p for p in products if is_gluten_free(p)]
            logger.info(f"    → After gluten filter: {len(products)}")

        # Filter by exclusions
        for exclusion in analysis.exclusions:
            if exclusion == 'sugar':
                products = [p for p in products if is_sugar_free(p)]
            elif exclusion == 'caffeine':
                products = [p for p in products if is_caffeine_free(p)]

        # Take top N by price (cheapest first for budget-conscious)
        products = sorted(products, key=lambda p: p.get('price', 999))[:max_per_category]

        # Tag products with metadata
        for p in products:
            p['_category'] = product_type
            p['_priority'] = PRODUCT_PRIORITY.get(product_type, 50)

        all_products.extend(products)

    # Calculate total
    total_price = sum(p.get('price', 0) for p in all_products)

    # Check budget and drop if needed
    if analysis.budget:
        if total_price <= analysis.budget:
            result.budget_status = "under"
            logger.info(f"✅ Budget OK: {total_price}₾ ≤ {analysis.budget}₾")
        else:
            result.budget_status = "over"
            logger.info(f"⚠️ Over budget: {total_price}₾ > {analysis.budget}₾ - dropping low priority items")

            # Drop lowest priority products until under budget
            all_products.sort(key=lambda p: p.get('_priority', 0))
            while total_price > analysis.budget and all_products:
                dropped_product = all_products.pop(0)  # Remove lowest priority
                dropped_category = dropped_product.get('_category', 'unknown')
                result.dropped_products.append(dropped_category)
                total_price = sum(p.get('price', 0) for p in all_products)
                logger.info(f"  → Dropped {dropped_category}, new total: {total_price}₾")

            if total_price <= analysis.budget:
                result.budget_status = "under_after_drops"

    # Add warnings for beginners requesting too many products
    if analysis.is_beginner and len(analysis.products_requested) > 2:
        result.warnings.append("beginner_overload")
        logger.info("⚠️ Warning: Beginner requesting many products")

    # Sort final results by priority (high priority first)
    all_products.sort(key=lambda p: p.get('_priority', 0), reverse=True)

    result.products = all_products
    result.total_price = total_price

    logger.info(f"🏁 Constraint search complete: {len(result.products)} products, "
                f"total={result.total_price}₾, status={result.budget_status}")

    return result


# =============================================================================
# DIETARY FILTER HELPERS
# =============================================================================

def is_lactose_free(product: Dict) -> bool:
    """Check if product is lactose-free based on name/keywords"""
    name = (product.get('name', '') + ' ' + product.get('brand', '')).lower()

    # Definitely lactose-free
    if any(word in name for word in ['isolate', 'plant', 'vegan', 'soy', 'pea', 'rice']):
        return True

    # Definitely has lactose
    if 'whey' in name and 'isolate' not in name:
        return False  # Whey concentrate has lactose

    if 'casein' in name:
        return False  # Casein is milk protein

    if 'mass' in name or 'gainer' in name:
        return False  # Usually contain milk

    # Default: non-dairy products are OK
    return True


def is_vegan(product: Dict) -> bool:
    """Check if product is vegan"""
    name = (product.get('name', '') + ' ' + product.get('brand', '')).lower()

    # Definitely vegan
    if any(word in name for word in ['plant', 'vegan', 'pea', 'soy', 'rice', 'hemp']):
        return True

    # Definitely not vegan
    if any(word in name for word in ['whey', 'casein', 'egg', 'beef', 'collagen']):
        return False

    # Creatine, vitamins, etc. are typically vegan-friendly
    if any(word in name for word in ['creatine', 'vitamin', 'mineral', 'caffeine']):
        return True

    return False  # Default assume not vegan


def is_gluten_free(product: Dict) -> bool:
    """Check if product is gluten-free"""
    name = (product.get('name', '') + ' ' + product.get('brand', '')).lower()

    # Most supplements are gluten-free
    # Only wheat-based products contain gluten
    if 'wheat' in name or 'barley' in name or 'oat' in name:
        return False

    return True


def is_sugar_free(product: Dict) -> bool:
    """Check if product is sugar-free"""
    name = (product.get('name', '') + ' ' + product.get('brand', '')).lower()

    # Indicators of sugar-free
    if any(word in name for word in ['zero', 'sugar free', 'no sugar', 'უშაქრო']):
        return True

    # Mass gainers typically have sugar
    if 'gainer' in name or 'mass' in name:
        return False

    # Most protein powders are low sugar
    return True


def is_caffeine_free(product: Dict) -> bool:
    """Check if product is caffeine-free"""
    name = (product.get('name', '') + ' ' + product.get('brand', '')).lower()

    # Products that typically contain caffeine
    if any(word in name for word in ['preworkout', 'pre-workout', 'energy', 'caffeine', 'კოფეინ']):
        return False

    # Fat burners often contain caffeine
    if 'fat burner' in name or 'thermogenic' in name:
        return False

    return True
