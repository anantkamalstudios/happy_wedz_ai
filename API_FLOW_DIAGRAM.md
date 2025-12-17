# API Flow: How the New Structure Works

## Request Flow

```
GET /api/recommendations/<user_id>
    ↓
┌─────────────────────────────────────┐
│  _ensure_rec_shape(recommendation)  │
│  - Fetch vendor_subcategory_data    │
│  - Return simplified vendor with    │
│    ONLY vendor_subcategory_data     │
│    array (no duplicates!)           │
└─────────────────────────────────────┘
    ↓
    ↓ (vendor list with only vendor_subcategory_data)
    ↓
┌─────────────────────────────────────┐
│  categorize_vendors(vendors)        │
│  - For each vendor:                 │
│    * Get vendor_subcategory_data    │
│    * Flatten into category items    │
│    * Each item gets final_score     │
│      and rank from vendor           │
│  - Return categories with items     │
└─────────────────────────────────────┘
    ↓
    ↓ (vendor_categories with items)
    ↓
┌─────────────────────────────────────┐
│  fill_empty_categories(...)         │
│  - For empty categories:            │
│    * Find matching vendor types     │
│    * Flatten & add subcategory      │
│      items to category              │
│  - Keep top 10 items per category   │
└─────────────────────────────────────┘
    ↓
    ↓ (complete vendor_categories)
    ↓
┌─────────────────────────────────────┐
│  jsonify(response)                  │
│  - Return vendor_categories         │
│  - Each item has:                   │
│    * vendor_subcategory_id (PK)     │
│    * attributes (no dup)            │
│    * media (no dup)                 │
│    * scores                         │
└─────────────────────────────────────┘
    ↓
Sent to Frontend
```

## Data Transformation Steps

### Step 1: Normalize Recommendations
**Input**: Raw recommendation from engine
```python
{
    "id": 332,
    "businessName": "Nova Krishnan",
    "city": "Dubai...",
    "vendor_type_name": "Bridal",
    "attributes": {...},  # From recommendation engine
    "media": [...],       # From recommendation engine
    "final_score": 1.0,
    "rank": 31
}
```

**`_ensure_rec_shape()` Output**: Simplified with DB data
```python
{
    "vendor_subcategory_data": [
        {
            "vendor_subcategory_id": 15,    # From DB
            "id": 15,
            "vendor_id": 332,
            "attributes": {...},             # From DB
            "media": [...]                   # From DB
        }
    ],
    "type": "vendor",
    "vendor_type_name": "Bridal",
    "final_score": 1.0,
    "rank": 31
}
```

### Step 2: Categorize Vendors
**Input**: Normalized vendors from Step 1

**Process**:
1. For vendor with `vendor_type_name = "Bridal"`
2. Get category key = "bridal" (from TYPE_MAP)
3. Extract `vendor_subcategory_data` array
4. For each item in array:
   - Add vendor's `final_score` and `rank`
   - Add to `categories["bridal"]["items"]`

**Output**: Each category has subcategory items (not vendors)
```python
{
    "bridal": {
        "items": [
            {
                "vendor_subcategory_id": 15,
                "id": 15,
                "vendor_id": 332,
                "attributes": {...},
                "media": [...],
                "final_score": 1.0,
                "rank": 31
            }
        ]
    }
}
```

### Step 3: Fill Empty Categories
**Input**: Categories with some empty

**Process**:
1. For each empty category:
   - Find vendors matching expected types
   - Flatten their subcategory items
   - Add to this category
2. Keep top 10 items per category

**Output**: All categories filled
```python
{
    "bridal": {
        "items": [item1, item2, ...]      # 10 items
    },
    "photography": {
        "items": [item10, item11, ...]    # 10 items
    },
    "jewelry": {
        "items": [item20, item21, ...]    # 10 items
    }
}
```

## Frontend Interaction Flow

### User Clicks on Vendor Card

```
┌──────────────────────────┐
│  User clicks card        │
│  (item = subcategory)    │
└───────────┬──────────────┘
            ↓
┌──────────────────────────┐
│  Extract ID:             │
│  vendorSubcategoryId =   │
│    item.vendor_subcat_id │
└───────────┬──────────────┘
            ↓
┌──────────────────────────┐
│  POST /interact          │
│  {                       │
│    user_id: 152,         │
│    vendor_subcat_data_id │
│      : vendorSubcatId,   │
│    action: "click"       │
│  }                       │
└───────────┬──────────────┘
            ↓
┌──────────────────────────┐
│  Backend Records         │
│  Interaction:            │
│  - user_id = 152         │
│  - vendor_subcat_id = 15 │
│  - action = click        │
│  - timestamp = now       │
└──────────────────────────┘
```

### Recommendation Generation (Next Time)

```
┌──────────────────────────────┐
│  User requests new recs      │
│  GET /recommendations/152    │
└───────────┬──────────────────┘
            ↓
┌──────────────────────────────┐
│  Fetch interactions:         │
│  - All records with          │
│    user_id = 152             │
│  - Extract user preferences  │
└───────────┬──────────────────┘
            ↓
┌──────────────────────────────┐
│  Query recommendations:      │
│  - Use preference data       │
│  - Score vendors             │
│  - Return top recommendations│
└───────────┬──────────────────┘
            ↓
┌──────────────────────────────┐
│  Return in new format:       │
│  - No duplicates             │
│  - Only subcategory data     │
│  - vendor_subcategory_id as PK│
└──────────────────────────────┘
```

## Key Points

### Why Flatten?
```
❌ BEFORE:
Item 1 = Vendor
  ├── metadata (final_score, rank)
  └── subcategory_data
      └── [0] = actual data to display

Frontend sees: Must nest one level deep, confusing structure

✅ AFTER:
Item 1 = Vendor Subcategory
  ├── vendor_subcategory_id (primary key)
  ├── metadata (final_score, rank)
  └── attributes, media (direct access)

Frontend sees: Flat structure, all data at same level
```

### Why No Duplicates?
```
❌ BEFORE:
Vendor Object
├── attributes {...}
├── media [...]
└── subcategory_data[0]
    ├── attributes {...}  ← SAME DATA
    └── media [...]       ← SAME DATA

Result: 50% duplicate data in every response

✅ AFTER:
Subcategory Item
├── attributes {...}     ← ONCE
└── media [...]          ← ONCE

Result: Each field appears exactly once
```

### Why vendor_subcategory_id?
```
❌ Ambiguous IDs:
- item.id could be vendor_subcategory_id
- item.vendor_id is the vendor ID
- item.vendor_subcategory_id is subcategory data ID
- Which one to use? 🤔

✅ Clear PK:
- item.vendor_subcategory_id is the primary key
- Use for all interactions
- Use for all recommendations
- No ambiguity 👍
```

## Summary

1. **API receives recommendation**: Raw vendor object with some duplicate data
2. **_ensure_rec_shape**: Fetches DB data, returns simplified vendor with vendor_subcategory_data
3. **categorize_vendors**: Flattens subcategory items into categories
4. **fill_empty_categories**: Adds more items from fallback vendors
5. **Response sent**: Clean, no duplicates, clear primary keys
6. **Frontend uses**: vendor_subcategory_id for all interactions
7. **Next recommendation**: System uses interaction history with vendor_subcategory_id

All clean, efficient, and unambiguous! 🎉
