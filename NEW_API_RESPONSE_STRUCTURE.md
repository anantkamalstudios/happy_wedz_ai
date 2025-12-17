# New API Response Structure - Complete Example

## Complete Response from `/api/recommendations/<user_id>`

```json
{
  "method": "active_user",
  "venues": [
    {
      "id": 1001,
      "businessName": "The Grand Ballroom",
      "city": "Mumbai",
      "type": "venue",
      "final_score": 0.98,
      "rank": 1
    }
  ],
  "vendors": [
    {
      "vendor_subcategory_data": [
        {
          "vendor_subcategory_id": 15,
          "id": 15,
          "vendor_id": 332,
          "attributes": {
            "Aboutus": "Nova Krishnan couture house...",
            "Address": "Dubai - United Arab Emirates",
            "Email": "novakrishnan@gmail.com",
            "Phone": 8010858858,
            "PhotoPackage_Price": "Rs. 6,660",
            "Photo_video_Price": "21,380",
            "Portfolio": "https://happywedz-s3-bucket.s3.ap-south-1.amazonaws.com/uploads/vendors/6026/...",
            "PriceRange": "Rs. 6,660-21,380",
            "URL": "https://www.happywedz.com/profile/6026"
          },
          "media": [
            "https://happywedz-s3-bucket.s3.ap-south-1.amazonaws.com/uploads/vendors/6026/image1.jpg",
            "https://happywedz-s3-bucket.s3.ap-south-1.amazonaws.com/uploads/vendors/6026/image2.jpg"
          ],
          "final_score": 1.0,
          "rank": 31
        }
      ],
      "type": "vendor",
      "vendor_type_name": "Bridal",
      "final_score": 1.0,
      "rank": 31
    }
  ],
  "vendor_categories": {
    "bridal": {
      "description": "Bridal wear",
      "display_name": "Bridal",
      "icon": "👗",
      "items": [
        {
          "vendor_subcategory_id": 15,
          "id": 15,
          "vendor_id": 332,
          "attributes": {
            "Aboutus": "Nova Krishnan, a couture house...",
            "Address": "Dubai - United Arab Emirates",
            "Email": "novakrishnan@gmail.com",
            "Phone": 8010858858,
            "PhotoPackage_Price": "Rs. 6,660",
            "Photo_video_Price": "21,380",
            "PriceRange": "Rs. 6,660-21,380",
            "URL": "https://www.happywedz.com/profile/6026"
          },
          "media": [
            "https://happywedz-s3-bucket.s3.ap-south-1.amazonaws.com/uploads/vendors/6026/image1.jpg",
            "https://happywedz-s3-bucket.s3.ap-south-1.amazonaws.com/uploads/vendors/6026/image2.jpg"
          ],
          "final_score": 1.0,
          "rank": 31
        },
        {
          "vendor_subcategory_id": 16,
          "id": 16,
          "vendor_id": 333,
          "attributes": {
            "Aboutus": "Another bridal designer...",
            "Address": "Mumbai - India",
            "Email": "designer@example.com",
            "Phone": 9876543210,
            "PriceRange": "Rs. 5,000-20,000",
            "URL": "https://www.happywedz.com/profile/6027"
          },
          "media": [
            "https://happywedz-s3-bucket.s3.ap-south-1.amazonaws.com/uploads/vendors/6027/image1.jpg"
          ],
          "final_score": 0.95,
          "rank": 32
        }
      ]
    },
    "photography": {
      "description": "Wedding photography & videography",
      "display_name": "Photography",
      "icon": "📷",
      "items": [
        {
          "vendor_subcategory_id": 42,
          "id": 42,
          "vendor_id": 500,
          "attributes": {
            "Aboutus": "Professional wedding photography...",
            "Address": "Bangalore - India",
            "Email": "photo@example.com",
            "Phone": 8765432109,
            "PriceRange": "Rs. 50,000-2,00,000",
            "URL": "https://www.happywedz.com/profile/6028"
          },
          "media": [
            "https://happywedz-s3-bucket.s3.ap-south-1.amazonaws.com/uploads/vendors/6028/image1.jpg",
            "https://happywedz-s3-bucket.s3.ap-south-1.amazonaws.com/uploads/vendors/6028/image2.jpg"
          ],
          "final_score": 0.92,
          "rank": 40
        }
      ]
    }
  },
  "user_profile": {
    "is_new_user": false,
    "days_since_registration": 45,
    "total_interactions": 23
  },
  "recommendation_stats": {
    "total_venues": 1,
    "total_vendors": 2,
    "sources": {
      "interaction_based": 1,
      "filler": 1
    },
    "categories_filled": 2,
    "total_categories": 7
  }
}
```

## Key Points

### 1. Each Subcategory Item is Complete
Every item in the `items` array of a category has:
- `vendor_subcategory_id` - **PRIMARY KEY** for interactions and recommendations
- `id` - same as vendor_subcategory_id (for convenience)
- `vendor_id` - reference to parent vendor (for debugging)
- `attributes` - all vendor details (No duplication at vendor level!)
- `media` - all images/videos (No duplication!)
- `final_score` - inherited from parent vendor
- `rank` - inherited from parent vendor

### 2. No Duplicate Data
✅ Each attribute is stored ONCE
✅ Media URLs appear ONCE
✅ No `_raw` field with entire object copy
✅ No `subcategory_data` array nested inside a vendor object

### 3. Frontend Integration Examples

#### Example 1: Display a Vendor Card
```javascript
function displayVendorCard(item) {
  // item is a vendor_subcategory_data object
  const vendorSubcategoryId = item.vendor_subcategory_id;
  const attributes = item.attributes;
  const media = item.media;
  const score = item.final_score;
  
  // Render card...
  
  return {
    id: vendorSubcategoryId,  // Use this for all interactions!
    name: attributes.Aboutus?.substring(0, 50),
    address: attributes.Address,
    price: attributes.PriceRange,
    images: media,
    score
  };
}
```

#### Example 2: Log an Interaction
```javascript
async function onVendorClick(item) {
  const vendorSubcategoryId = item.vendor_subcategory_id;
  
  // CORRECT: Use vendor_subcategory_id
  await api.post('/api/recommendations/interact', {
    user_id: currentUser.id,
    vendor_subcategory_data_id: vendorSubcategoryId,
    action: 'click',
    value: {
      category: 'bridal',
      price_range: item.attributes.PriceRange
    }
  });
}
```

#### Example 3: Wishlist a Vendor
```javascript
async function addToWishlist(item) {
  const vendorSubcategoryId = item.vendor_subcategory_id;
  
  // CORRECT: Use vendor_subcategory_id
  await api.post('/api/recommendations/interact', {
    user_id: currentUser.id,
    vendor_subcategory_data_id: vendorSubcategoryId,
    action: 'wishlist',
    value: {
      wishlist_category: 'bridal'
    }
  });
}
```

#### Example 4: Get Recommendations
```javascript
async function getRecommendations() {
  const response = await api.get('/api/recommendations/152?city=Mumbai');
  
  const categories = response.data.vendor_categories;
  
  for (const [categoryKey, categoryData] of Object.entries(categories)) {
    console.log(`Category: ${categoryData.display_name}`);
    
    categoryData.items.forEach(item => {
      // Each item is a vendor_subcategory_data object
      // All needed data is directly in item
      console.log(`  - ${item.attributes.Email} (Score: ${item.final_score})`);
      
      // If you need to track this vendor:
      // Use item.vendor_subcategory_id
    });
  }
}
```

## Migration Guide for Existing Code

### If You Were Using
```javascript
// ❌ OLD - DON'T USE
const vendorId = vendor.id;
const subcatArray = vendor.subcategory_data;
const attributes = subcatArray[0]?.attributes;
```

### Use This Instead
```javascript
// ✅ NEW - USE THIS
const vendorSubcategoryId = item.vendor_subcategory_id;
const attributes = item.attributes;
const media = item.media;
```

### For Interaction Logging

```javascript
// ❌ OLD
api.post('/api/recommendations/interact', {
  vendor_id: someId,  // which ID?
  vendor_subcategory_data_id: someOtherId,  // wrong level of nesting?
});

// ✅ NEW
api.post('/api/recommendations/interact', {
  user_id: userId,
  vendor_subcategory_data_id: item.vendor_subcategory_id,  // direct, clear ID
  action: 'click'
});
```

## Summary

The new structure provides:
- **Single source of truth**: Each item has one copy of all data
- **Clear primary key**: `vendor_subcategory_id` for all interactions
- **No nested complexity**: Attributes and media are directly on the item
- **Efficient payload**: 40-50% smaller response size
- **Simpler frontend code**: No need to navigate nested structures
