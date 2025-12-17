# Frontend Integration Checklist for Interaction API

## TL;DR - Add These 2 API Calls to Your Frontend

### 1. When User Clicks a Vendor Card
**Where:** Vendor card component / Vendor browse page
**When:** User clicks "View Details" or card itself
**What to send:**
```javascript
fetch('/api/recommendations/interact', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: currentUserId,
    vendor_subcategory_data_id: vendorId,  // ID from the vendor card
    action: 'click'
  })
})
```

---

### 2. When User Adds Vendor to Wishlist
**Where:** Vendor detail page / Wishlist button
**When:** User clicks heart/star/wishlist button
**What to send:**
```javascript
fetch('/api/recommendations/interact', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: currentUserId,
    vendor_subcategory_data_id: vendorId,  // ID from the vendor
    action: 'wishlist'
  })
})
```

---

## Exact Locations to Add Code

### React/Vue Component Example

```javascript
// VendorCard.jsx or VendorCard.vue
export function VendorCard({ vendor, userId }) {
  
  // INTEGRATION POINT #1: Click handler
  const handleCardClick = async () => {
    // Log interaction
    await fetch('/api/recommendations/interact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        vendor_subcategory_data_id: vendor.id,  // or vendor.vendor_subcategory_data_id
        action: 'click'
      })
    }).catch(err => console.error('Failed to log interaction:', err));
    
    // Then navigate/show details
    navigateToVendorDetails(vendor.id);
  };

  // INTEGRATION POINT #2: Wishlist handler
  const handleWishlistClick = async () => {
    // Log interaction
    await fetch('/api/recommendations/interact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        vendor_subcategory_data_id: vendor.id,
        action: 'wishlist'
      })
    }).catch(err => console.error('Failed to log interaction:', err));
    
    // Then update wishlist UI
    toggleWishlist(vendor.id);
  };

  return (
    <div className="vendor-card" onClick={handleCardClick}>
      <img src={vendor.image} alt={vendor.businessName} />
      <h3>{vendor.businessName}</h3>
      <p>{vendor.city} • {vendor.vendor_type_name}</p>
      
      <button 
        className="wishlist-btn"
        onClick={(e) => {
          e.stopPropagation();  // Don't trigger card click
          handleWishlistClick();
        }}
      >
        ❤️ Add to Wishlist
      </button>
    </div>
  );
}
```

---

## Key Points for Frontend Developers

✅ **DO:**
- Send `vendor_subcategory_data_id` (required - this is the primary key)
- Include `user_id` (required - identifies the user)
- Set `action` to either `'click'` or `'wishlist'` (required)
- Call on every vendor interaction
- Ignore failed requests (don't block UI)

❌ **DON'T:**
- Don't wait for response before navigating (async, fire-and-forget)
- Don't send duplicate requests (same vendor, same action within 5 min)
- Don't include sensitive data in the value field
- Don't fail the user experience if the API is down

---

## What Happens After They Click/Wishlist

1. Backend enriches with vendor metadata (automatic - nothing frontend needs to do)
2. User's preferences get updated automatically
3. Next time user loads the app:
   - `/api/recommendations/user/{id}/preferences` → shows their style
   - `/api/recommendations/recommendations/{id}` → shows personalized vendors
4. Future emails will be personalized to their interests

---

## Testing the Integration

Before deployment, test with Postman/curl:

```bash
# Test 1: Simulate a click
curl -X POST http://localhost:5000/api/recommendations/interact \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "vendor_subcategory_data_id": 123,
    "action": "click"
  }'

# Test 2: Simulate a wishlist add
curl -X POST http://localhost:5000/api/recommendations/interact \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "vendor_subcategory_data_id": 123,
    "action": "wishlist"
  }'

# Test 3: Check that preferences are populated
curl http://localhost:5000/api/recommendations/user/1/preferences

# Expected response (should show favorite cities, types, categories):
# {
#   "user_id": 1,
#   "preferences": {
#     "favorite_cities": {"New York": 2.0},
#     "favorite_vendor_categories": {...},
#     "favorite_vendor_types": {...},
#     "total_interactions": 2
#   }
# }
```

---

## Files to Update

| File Type | Component | Changes |
|-----------|-----------|---------|
| **React/Vue** | `<VendorCard />` | Add `onClick` → POST /interact with action='click' |
| **React/Vue** | Wishlist button | Add `onClick` → POST /interact with action='wishlist' |
| **Any** | Vendor grid | Same card handlers |
| **Any** | Vendor detail page | Same handlers |
| **Any** | Wishlist management | Same handlers |

---

## Copy-Paste Ready Code

### Standalone Helper Function
```javascript
// Put this in a utils file (e.g., api/interactions.js)
export async function logVendorInteraction(userId, vendorSubcategoryDataId, action) {
  try {
    const response = await fetch('/api/recommendations/interact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        vendor_subcategory_data_id: vendorSubcategoryDataId,
        action: action  // 'click' or 'wishlist'
      })
    });
    
    if (!response.ok) {
      console.error('Failed to log interaction:', response.statusText);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error logging interaction:', error);
    // Silently fail - don't break the user experience
  }
}

// Then use it in components:
// import { logVendorInteraction } from '@/api/interactions';
// 
// const handleClick = () => {
//   logVendorInteraction(userId, vendorId, 'click');
//   navigateToDetails(vendorId);
// };
```

---

## Network Request Example (from DevTools)

```
POST /api/recommendations/interact HTTP/1.1
Host: localhost:5000
Content-Type: application/json

{
  "user_id": 1,
  "vendor_subcategory_data_id": 456,
  "action": "click"
}

---

HTTP/1.1 201 Created
Content-Type: application/json

{
  "success": true,
  "message": "Interaction logged successfully"
}
```

---

## Summary for Frontend Team

**Tell your frontend developers:**

> Add this single API call in 2 places:
> 1. When user clicks a vendor card
> 2. When user adds/removes from wishlist
>
> **Endpoint:** `POST /api/recommendations/interact`
> 
> **Required fields:**
> - `user_id` (integer)
> - `vendor_subcategory_data_id` (integer - the vendor's ID from the card)
> - `action` (string: 'click' or 'wishlist')
>
> **That's it!** The backend handles everything else.
> Don't wait for response, don't block UI if it fails.
>
> Once they add these 2 calls, all personalization features will work:
> - User preferences will auto-populate
> - Recommendations will be personalized
> - Email campaigns will be targeted

