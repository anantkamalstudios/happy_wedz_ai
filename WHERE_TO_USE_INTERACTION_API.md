# Where to Apply the Interaction API in Your App

## Frontend Integration Points

### 1️⃣ When User Clicks on a Vendor Card
**Location:** Vendor browse/search page, vendor card component

**Action:**
```javascript
// When user clicks "View Details" on a vendor card
function onVendorCardClick(vendorSubcategoryDataId) {
  fetch('/api/recommendations/interact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: currentUserId,
      vendor_subcategory_data_id: vendorSubcategoryDataId,
      action: 'click',  // user is viewing details
      value: {
        // Optional: any extra metadata you want to track
        page: 'search',
        position: 5,  // position in results
      }
    })
  })
  .then(r => r.json())
  .then(data => console.log('Interaction logged:', data))
}
```

**Result:** 
- System learns: User clicked on photographers in New York
- Preferences updates: Photography type gets +2.5 weight

---

### 2️⃣ When User Adds Vendor to Wishlist
**Location:** Vendor detail page, wishlist button

**Action:**
```javascript
// When user clicks heart/wishlist button
function onAddToWishlist(vendorSubcategoryDataId) {
  fetch('/api/recommendations/interact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: currentUserId,
      vendor_subcategory_data_id: vendorSubcategoryDataId,
      action: 'wishlist',  // stronger signal than click
      value: {
        // Track that they explicitly marked as favorite
        intention: 'seriously_considering'
      }
    })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      // Show "Added to wishlist" toast
      showToast('Added to wishlist!');
    }
  })
}
```

**Result:**
- System learns: User loves this vendor (wishlist > click)
- Preferences updates: This vendor's type/city gets +3.0 weight
- Recommendations: More vendors like this vendor will appear

---

### 3️⃣ Display User Preferences (Profile Page)
**Location:** User profile → "My Preferences" or "My Style"

**Action:**
```javascript
// Load user's discovered preferences
async function loadUserPreferences(userId) {
  const response = await fetch(`/api/recommendations/user/${userId}/preferences`);
  const data = await response.json();
  
  const { preferences } = data;
  
  // Display favorite cities
  console.log('You like vendors in:', Object.keys(preferences.favorite_cities));
  // → "New York", "Los Angeles"
  
  // Display favorite vendor types
  console.log('You love:', Object.keys(preferences.favorite_vendor_types));
  // → "Photography", "Catering"
  
  // Display favorite categories
  console.log('You\'re interested in:', Object.keys(preferences.favorite_vendor_categories));
  // → "Studio", "Restaurant"
  
  // Render preference cards
  renderPreferenceCards(preferences);
}

// Example UI rendering
function renderPreferenceCards(preferences) {
  const html = `
    <div class="user-style">
      <h2>Your Wedding Style</h2>
      
      <section class="preference-section">
        <h3>Favorite Cities</h3>
        <div class="chips">
          ${Object.entries(preferences.favorite_cities)
            .map(([city, score]) => 
              `<span class="chip">${city} <small>${score.toFixed(1)}✓</small></span>`
            ).join('')}
        </div>
      </section>
      
      <section class="preference-section">
        <h3>Vendor Types You Love</h3>
        <div class="chips">
          ${Object.entries(preferences.favorite_vendor_types)
            .map(([type, score]) => 
              `<span class="chip">${type}</span>`
            ).join('')}
        </div>
      </section>
      
      <section class="preference-section">
        <h3>Categories of Interest</h3>
        <div class="chips">
          ${Object.entries(preferences.favorite_vendor_categories)
            .map(([cat, score]) => 
              `<span class="chip">${cat}</span>`
            ).join('')}
        </div>
      </section>
      
      <p>Based on your ${preferences.total_interactions} vendor interactions</p>
    </div>
  `;
  document.getElementById('preference-container').innerHTML = html;
}
```

**Result:**
- Users see what the system learned about them
- Increases engagement (users like seeing personalization)
- Shows system is working in real-time

---

### 4️⃣ Display Personalized Recommendations (Main Feed)
**Location:** Home page / Discover tab

**Action:**
```javascript
// Load personalized recommendations
async function loadRecommendations(userId) {
  const response = await fetch(`/api/recommendations/recommendations/${userId}?limit=50`);
  const data = await response.json();
  
  const { venues, vendor_categories } = data;
  
  // Display recommended venues (sorted by preference)
  renderSection('Top Venues', venues);
  
  // Display vendors by category
  for (const [category, categoryData] of Object.entries(vendor_categories)) {
    renderSection(
      `${category} (Based on your interests)`,
      categoryData.items
    );
  }
}

// Example rendering
function renderSection(title, vendors) {
  const cards = vendors
    .map(v => `
      <div class="vendor-card" onclick="onVendorClick(${v.vendor_subcategory_data_id})">
        <h4>${v.businessName}</h4>
        <p>${v.city} • ${v.vendor_type_name}</p>
        <p class="source-badge">${v.source}</p>
        ${v.final_score > 3 ? '<span class="badge-hot">Popular in your area</span>' : ''}
      </div>
    `)
    .join('');
  
  document.getElementById('feed').innerHTML += `
    <section>
      <h3>${title}</h3>
      <div class="vendor-grid">${cards}</div>
    </section>
  `;
}
```

**Result:**
- Users see vendors matched to their interests
- Much better experience than generic recommendations
- Increases conversion (relevant vendors = more bookings)

---

### 5️⃣ Email Campaigns (Backend)
**Location:** Email service using preferences data

**Action:**
```python
# In email_automation/services/send_recommendations.py
def send_personalized_email(user_id):
    # Get user's preferences
    prefs = get_user_preferences(user_id)
    
    # Get top 5 recommended vendors
    recs = get_recommendations(user_id, limit=5)
    
    # Send email: "Vendors you'll love"
    email_template = {
        'subject': f'New vendors in {prefs["favorite_cities"][0]}',
        'vendors': recs,
        'personalization': {
            'top_city': prefs['favorite_cities'][0],
            'top_category': prefs['favorite_vendor_categories'][0],
        }
    }
    
    send_email(user_id, email_template)
```

**Result:**
- Users get relevant email recommendations
- Higher email engagement rates
- More vendor discovery through email

---

## API Call Summary Table

| Where | What | Endpoint | When |
|-------|------|----------|------|
| Vendor browse | Log click | `POST /interact` | User clicks vendor card |
| Vendor detail | Add to wishlist | `POST /interact` | User clicks wishlist button |
| Profile page | Show preferences | `GET /preferences` | Page load |
| Home/Discover | Show recommendations | `GET /recommendations/<id>` | Page load, refresh |
| Background job | Email recommendations | (uses both) | Daily/weekly |
| Analytics | Track conversions | (uses interactions) | Continuously |

---

## Data Flow in Your App

```
┌──────────────────────────────────────────────────────────────┐
│                     FRONTEND                                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Vendor Browse    │  │ Wishlist         │                │
│  │ (grid/search)    │  │ (heart button)   │                │
│  └────────┬─────────┘  └────────┬─────────┘                │
│           │ click                │ add                       │
│           └────────────┬─────────┘                          │
│                        │                                     │
│           POST /api/recommendations/interact                │
│           {                                                  │
│             user_id: 1,                                      │
│             vendor_subcategory_data_id: 456,               │
│             action: "click" | "wishlist",                  │
│             value: {...}                                    │
│           }                                                  │
│                        │                                     │
├────────────────────────┼─────────────────────────────────────┤
│                        ↓                                     │
│           BACKEND (Python/Flask)                            │
│           • Validate & enrich with vendor metadata          │
│           • Save to DB + cache                              │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                        │                                     │
│        ┌───────────────┼───────────────┐                    │
│        ↓               ↓               ↓                     │
│  ┌───────────┐  ┌────────────┐  ┌─────────────┐           │
│  │ Profile   │  │ Discover   │  │ Analytics   │           │
│  │ (Prefs)   │  │ (Recomm.)  │  │ Dashboard   │           │
│  └───────────┘  └────────────┘  └─────────────┘           │
│        ↑               ↑               ↑                     │
│  GET /preferences  GET /recommendations  (reports)         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Testing the Integration

### Test 1: Log an interaction
```bash
curl -X POST http://localhost:5000/api/recommendations/interact \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "vendor_subcategory_data_id": 456,
    "action": "click",
    "value": {}
  }'
```

**Expected response:**
```json
{
  "success": true,
  "message": "Interaction logged successfully"
}
```

### Test 2: Check preferences
```bash
curl http://localhost:5000/api/recommendations/user/1/preferences
```

**Expected response (BEFORE enrichment was broken):**
```json
{
  "user_id": 1,
  "preferences": {
    "favorite_cities": {},  // ❌ EMPTY
    "favorite_vendor_categories": {},
    "favorite_vendor_types": {},
    "total_interactions": 1
  }
}
```

**Expected response (AFTER enrichment is fixed):**
```json
{
  "user_id": 1,
  "preferences": {
    "favorite_cities": {"New York": 2.0},  // ✅ POPULATED!
    "favorite_vendor_categories": {"Photography": 2.0},
    "favorite_vendor_types": {"Studio": 2.0},
    "total_interactions": 1
  }
}
```

### Test 3: Get recommendations
```bash
curl http://localhost:5000/api/recommendations/recommendations/1?limit=10
```

**Expected response:**
```json
{
  "user_id": 1,
  "recommendations": {
    "venues": [...],
    "vendor_categories": {
      "Photography": {
        "items": [
          {
            "id": 789,
            "businessName": "Studio NYC",
            "city": "New York",
            "final_score": 3.5,
            "source": "city_match"
          }
        ]
      }
    }
  }
}
```

---

## Summary

The interaction API is the **core of your personalization engine:**

1. **Frontend collects signals** when users click/wishlist vendors
2. **Backend enriches & stores** interactions with vendor metadata
3. **Preferences API** aggregates to show what users like
4. **Recommendations engine** uses preferences to rank vendors
5. **All features depend on this** data flow

With the enrichment you just added, the system now has complete visibility into user preferences and can provide truly personalized recommendations! 🎉

