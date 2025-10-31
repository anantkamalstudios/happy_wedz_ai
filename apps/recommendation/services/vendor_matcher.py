class VendorMatcher:
    """Smart vendor matching based on venue selections"""
    
    @staticmethod
    def get_vendors_for_venue_city(city, limit=5):
        """Get vendors in the same city as the venue"""
        from .cache import vendors_cache
        vendors = []
        for vendor_id, vendor in vendors_cache.items():
            if vendor['city'] == city:
                vendor_copy = vendor.copy()
                vendor_copy['source'] = 'venue_city_match'
                vendor_copy['score'] = vendor['rating'] * 1.5  # Boost for location match
                vendors.append(vendor_copy)
        
        return sorted(vendors, key=lambda x: x['score'], reverse=True)[:limit]