# Interaction API → Recommendation Engine Flow

## Overview
The `/api/recommendations/interact` API is the **data collection layer** that feeds the entire recommendation system. Here's how it works:

---

## 1. INTERACTION LOGGING (`POST /api/recommendations/interact`)
**Location:** `apps/recommendations/routes/interactions.py`

### What happens:
```
Frontend (User clicks vendor)
        ↓
POST /api/recommendations/interact
{
    "user_id": 1,
    "vendor_subcategory_data_id": 456,
    "action": "click" or "wishlist",
    "value": { ... }
}
        ↓
[ENRICHMENT] Look up vendor metadata from vendor_subcategory_data_id:
- Vendor's city
- Vendor's category
- Vendor's type
        ↓
[STORAGE] Save to database (UserInteraction table):
- Spam prevention (no duplicates within 5 min)
- Store in-memory cache (user_interactions_cache)
        ↓
Returns: {"success": true}
```

### Current Issue ❌
The `value` JSON is **NOT being enriched** with vendor metadata. This means:
- `value` stays as whatever the frontend sends (usually empty `{}`)
- Preference calculation has nothing to work with
- `favorite_cities`, `favorite_categories`, `favorite_types` all end up empty

---

## 2. PREFERENCE CALCULATION (`GET /api/recommendations/user/<user_id>/preferences`)
**Location:** `apps/recommendations/routes/preferences.py`
**Logic:** `apps/recommendations/services/recommendation_engine.py` → `UserPreferenceRecommender.calculate_weighted_preferences()`

### What happens:
```
GET /api/recommendations/user/1/preferences
        ↓
Fetch interactions from cache: user_interactions_cache[user_id]['interactions']
        ↓
For each interaction, extract from value JSON:
  - value['city']
  - value['vendor_type'] or value['type']
  - value['vendor_category'] or value['category']
        ↓
Build weighted Counters:
  - Recency weight: (3.0x if <1 day, 2.0x if <7 days, 1.0x if <30 days, 0.5x older)
  - Value fields get 2.0x multiplier
  - Returns: { cities: Counter, vendor_types: Counter, vendor_categories: Counter }
        ↓
Return formatted preferences:
{
    "favorite_cities": { "New York": 6.0, "Los Angeles": 4.5 },
    "favorite_vendor_categories": { "Catering": 8.0 },
    "favorite_vendor_types": { "Restaurant": 6.0 },
    "total_interactions": 6
}
```

### Current Issue ❌
Since `value` is empty, all Counters are empty → returns empty dicts

---

## 3. RECOMMENDATION ENGINE (`GET /api/recommendations/recommendations/<user_id>`)
**Location:** `apps/recommendations/routes/recommendations.py`
**Logic:** `apps/recommendations/services/recommendation_engine.py` → `HybridRecommendationEngine.get_recommendations()`

### What happens:
```
GET /api/recommendations/recommendations/1?limit=50
        ↓
Fetch user interactions from cache
        ↓
IF user has ≥2 interactions:
  PRIORITY 1: Interaction-based (vendors they clicked/wishlisted)
  ↓
  Calculate preferences from interactions
  ↓
  PRIORITY 2: City-based (vendors in their preferred cities)
  ↓
  PRIORITY 3: Type/Category-based (vendors matching their interests)
  ↓
  Score each vendor:
    - Wishlist interaction: 3.0 points
    - Click interaction: 2.5 points
    - City match: +0.5 points
    - Type/Category match: varies
  ↓
ELSE (< 2 interactions):
  Use fallback recommendations (popular vendors by region)
  ↓
Return: [
    {
        "id": 123,
        "businessName": "The Great Caterer",
        "city": "New York",
        "vendor_type_name": "Catering",
        "final_score": 3.5,
        "source": "user_history_wishlist"
    },
    ...
]
        ↓
Frontend displays personalized vendor cards
```

---

## 4. FULL END-TO-END FLOW

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                    │
│ User browses vendors, clicks on "The Great Caterer"        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ POST /api/recommendations/interact
                     │ {
                     │   "user_id": 1,
                     │   "vendor_subcategory_data_id": 456,
                     │   "action": "click",
                     │   "value": {}
                     │ }
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ INTERACTION API (interactions.py)                           │
│ • Validates input                                           │
│ • Spam check (duplicate within 5 min?)                      │
│ • [MISSING] Enrichment: fetch vendor metadata              │
│ • Save to DB + cache                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓ (stores in cache)
┌─────────────────────────────────────────────────────────────┐
│ IN-MEMORY CACHE (services/cache.py)                         │
│ user_interactions_cache[1] = {                              │
│   "interactions": [                                         │
│     {                                                       │
│       "vendor_subcategory_data_id": 456,                   │
│       "action": "click",                                    │
│       "value": { ... },  ← SHOULD CONTAIN: city, type, category
│       "created_at": datetime,                               │
│       "days_ago": 0                                         │
│     }                                                       │
│   ]                                                         │
│ }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ↓            ↓            ↓
    [A] [B]      [C]          [D]
    
    [A] GET /api/recommendations/user/1/preferences
        ↓
        Calculate preferences from cached interactions
        ↓
        Return: { favorite_cities, favorite_categories, ... }
        
    [B] GET /api/recommendations/recommendations/1
        ↓
        Use preferences to score vendors
        ↓
        Return: Personalized vendor list
        
    [C] Recommendation dashboard uses preferences
        ↓
        Display "Popular in your cities", etc.
        
    [D] A/B testing & analytics
        ↓
        Track which preferences lead to conversions
```

---

## Where to Apply / What Needs Fixing

### ✅ Currently Working:
- Interaction logging endpoint
- Duplicate prevention (5-min spam check)
- In-memory caching
- Database persistence

### ❌ Missing - ENRICHMENT STEP:
**File:** `apps/recommendations/routes/interactions.py`
**Function:** `interact()` around line 70-90

Add this logic:
```python
# After validating vendor_subcategory_data_id, before saving:
try:
    vsd = VendorSubcategoryData.query.get(subcat_id)
    if vsd:
        # Enrich value JSON with vendor metadata
        value_json["city"] = vsd.vendor.city  # or however it's stored
        value_json["vendor_type"] = vsd.vendor_type_name
        value_json["vendor_category"] = vsd.category_name
except Exception:
    # Log error but don't fail the interaction
    pass
```

This way:
1. **Preferences endpoint** will have data to extract → returns non-empty favorite_cities, etc.
2. **Recommendations engine** will have preferences to work with → better scoring
3. **A/B testing** can track which preferences drive conversions

---

## Impact on User Experience

**Without enrichment:**
- User clicks 10 vendors → all from different cities/categories
- Preferences are empty → can't identify patterns
- Recommendations are generic (fallback to all popular vendors)
- No personalization

**With enrichment:**
- User clicks 10 vendors → system extracts city/category/type
- Preferences show: "You like Photography studios in New York"
- Recommendations prioritize Photography in NYC
- Much better experience! ✨

