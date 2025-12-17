# How the Interaction API Powers Recommendations

## Quick Summary

**The `/api/recommendations/interact` endpoint is the foundation of personalization.** Here's what each component does:

---

## Three Main API Endpoints

### 1️⃣ LOG INTERACTION (POST /api/recommendations/interact)
**Where:** User clicks on a vendor card → Frontend sends:
```json
{
  "user_id": 1,
  "vendor_subcategory_data_id": 456,
  "action": "click",  // or "wishlist"
  "value": {}
}
```

**What it does:**
- Validates input
- **Enriches** with vendor metadata (city, vendor_type, category) ✨ NEW
- Prevents spam (no duplicate in last 5 min)
- Saves to DB + in-memory cache
- Returns `{"success": true}`

**Result:** User interaction stored with full vendor context

---

### 2️⃣ GET PREFERENCES (GET /api/recommendations/user/1/preferences)
**Where:** User's profile page to show "Your Preferences"

**What it does:**
- Fetches all interactions from cache
- Extracts city, vendor_type, vendor_category from each interaction
- Weights them by recency (recent = higher weight)
- Returns aggregated preferences:
```json
{
  "user_id": 1,
  "preferences": {
    "favorite_cities": {"New York": 6.0, "Los Angeles": 4.5},
    "favorite_vendor_categories": {"Catering": 8.0, "Photography": 5.0},
    "favorite_vendor_types": {"Restaurant": 6.0, "Studio": 4.0},
    "total_interactions": 6
  }
}
```

**Why it matters:** Shows users what the system learned about them

---

### 3️⃣ GET RECOMMENDATIONS (GET /api/recommendations/recommendations/1)
**Where:** Main feed/discover page to show personalized vendors

**Scoring logic (in order):**
1. **Direct history** (vendors they clicked/wishlisted) → Score: 2.5 (click) or 3.0 (wishlist)
2. **City match** (vendors in their favorite cities) → Score: 1.5-1.8
3. **Type/Category match** (Caterers, Photographers, etc.) → Score: 1.2-1.5
4. **Fallback** (popular vendors if insufficient interactions) → Score: 1.0

**Result:** Returns ranked list:
```json
{
  "venues": [...],  // sorted venues in top city
  "vendor_categories": {
    "Catering": { "items": [{...}, {...}] },
    "Photography": { "items": [{...}] },
    ...
  }
}
```

---

## Data Flow Visualization

```
┌─────────────┐
│  Frontend   │
│  User clicks│
│  vendor    │
└──────┬──────┘
       │ POST /interact + metadata
       ↓
┌─────────────────────────────────────┐
│  Interaction API (routes/...)        │ ← YOU JUST FIXED THIS
│  • Validate                          │   with enrichment
│  • Enrich with city/type/category   │
│  • Spam prevention                  │
│  • Save to DB + cache               │
└──────┬──────────────────────────────┘
       │ stores in
       ↓
┌─────────────────────────────────────┐
│  In-Memory Cache                     │
│  user_interactions_cache[1]          │
│    → interactions: [                 │
│      {                               │
│        action: "click"               │
│        value: {                      │
│          city: "New York"        ✨  │
│          vendor_type: "Catering" ✨  │
│          vendor_category: "..."  ✨  │
│        }                             │
│      }                               │
│    ]                                 │
└──────┬──────────────────────────────┘
       │
   ┌───┴───┬─────────┬──────────────┐
   ↓       ↓         ↓              ↓
┌──────┐ ┌────────┐ ┌────────────┐ ┌──────┐
│Prefs │ │Recomm. │ │ Dashboard  │ │A/B   │
│API   │ │Engine  │ │  Insights  │ │Test  │
└──────┘ └────────┘ └────────────┘ └──────┘
   ↓         ↓          ↓             ↓
Returns   Returns    Shows       Track
favorite  scored     "You        which
cities,   vendors    like..."    features
types                            convert
```

---

## Why This Matters

### Before (Without Enrichment) ❌
```
User clicks 10 vendors (various cities/types)
↓
Preferences: { favorite_cities: {}, favorite_types: {}, ... }
↓
Recommendations: Generic popular vendors
↓
User gets same recommendations as everyone
```

### After (With Enrichment) ✅
```
User clicks 10 vendors (various cities/types)
↓
Preferences: {
  favorite_cities: {"NYC": 8.0},
  favorite_types: {"Photography": 6.0},
  favorite_categories: {"Studio": 5.0}
}
↓
Recommendations: Photographers in NYC
↓
User gets truly personalized recommendations
```

---

## Where It's Applied

| Component | Uses Data From | Purpose |
|-----------|---|---|
| **Recommendations Feed** | Preferences + Interactions | Score & rank vendors |
| **Profile/Preferences** | Preferences API | Show user "your style" |
| **Discover Page** | Top 10 preferred cities | Filter vendors by user's geography |
| **Vendor Cards** | Interaction history | Show "trending with similar users" |
| **Email Campaigns** | Preferences | Send personalized vendor recommendations |
| **Analytics Dashboard** | All interactions | Track engagement patterns |

---

## Implementation Status

✅ **DONE:**
- Interaction logging endpoint
- Database persistence
- In-memory cache
- Preference calculation logic
- Recommendation engine
- Duplicate prevention

✅ **JUST ADDED:**
- **Metadata enrichment** in `/interact` endpoint
  - Extracts vendor city from Vendor model
  - Extracts vendor_type from VendorType model
  - Extracts category from VendorSubcategory model

🚀 **Result:** 
- Preferences endpoint will now return non-empty `favorite_cities`, `favorite_vendor_categories`, `favorite_vendor_types`
- Recommendations engine can properly score vendors based on user preferences
- Full personalization flow is now active!

