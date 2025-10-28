class VendorCategories:
    # Standard vendor categories for wedding planning
    CATEGORIES = {
        'photographer': {'display_name': 'Photography', 'description': 'Capture your special moments', 'priority': 1},
        'florist': {'display_name': 'Florists', 'description': 'Beautiful floral arrangements', 'priority': 2},
        'caterer': {'display_name': 'Catering', 'description': 'Delicious food for your guests', 'priority': 3},
        'decorator': {'display_name': 'Decorators', 'description': 'Transform your venue beautifully', 'priority': 4},
        'dj': {'display_name': 'DJ & Music', 'description': 'Keep the party going', 'priority': 5},
        'videographer': {'display_name': 'Videography', 'description': 'Professional wedding films', 'priority': 6},
        'makeup_artist': {'display_name': 'Makeup Artists', 'description': 'Look your absolute best', 'priority': 7},
        'mehendi_artist': {'display_name': 'Mehendi Artists', 'description': 'Beautiful henna designs', 'priority': 8},
        'band': {'display_name': 'Live Bands', 'description': 'Live music performances', 'priority': 9},
        'transport': {'display_name': 'Transportation', 'description': 'Arrive in style', 'priority': 10},
        'pandit': {'display_name': 'Pandits', 'description': 'Sacred ceremony guidance', 'priority': 11},
        'invitation_designer': {'display_name': 'Invitations', 'description': 'Beautiful wedding invitations', 'priority': 12},
        'jewellery': {'display_name': 'Jewellery', 'description': 'Stunning wedding jewellery', 'priority': 13},
        'choreographer': {'display_name': 'Choreographers', 'description': 'Perfect wedding dance', 'priority': 14},
        'other': {'display_name': 'Other Services', 'description': 'Additional wedding services', 'priority': 99}
    }
    
    TYPE_MAP = {
        # Photography-related
        "photo": "photographer", "photographer": "photographer", "photographers": "photographer",
        "photography": "photographer", "camera": "photographer",

        # Florist-related
        "florist": "florist", "florists": "florist", "floral": "florist", "flower": "florist", "flowers": "florist",

        # Caterer-related
        "cater": "caterer", "catering": "caterer", "caterer": "caterer", "caterers": "caterer", "food": "caterer",
        "cake": "caterer", "bakery": "caterer",

        # Decorator-related
        "decor": "decorator", "decorator": "decorator", "decorators": "decorator",
        "decoration": "decorator", "decorations": "decorator", "lighting": "decorator", "backdrop": "decorator",

        # DJ-related
        "dj": "dj", "dj & music": "dj", "dj and music": "dj", "music": "dj", "sound": "dj",

        # Videography-related
        "videographer": "videographer", "videography": "videographer", "video": "videographer", "film": "videographer",

        # Makeup-related
        "makeup": "makeup_artist", "makeup artist": "makeup_artist", "beauty": "makeup_artist", "stylist": "makeup_artist",

        # Mehendi-related
        "mehendi": "mehendi_artist", "mehendi artist": "mehendi_artist", "henna": "mehendi_artist",

        # Band-related
        "band": "band", "bands": "band", "musician": "band", "musicians": "band", "singer": "band",

        # Transport-related
        "transport": "transport", "transportation": "transport", "car": "transport", "vehicle": "transport",

        # Pandit-related
        "pandit": "pandit", "priest": "pandit", "officiant": "pandit",

        # Invitation-related
        "invitation": "invitation_designer", "invitations": "invitation_designer", "card": "invitation_designer",
        "cards": "invitation_designer", "printing": "invitation_designer", "invitation designer": "invitation_designer",

        # Jewellery-related
        "jewel": "jewellery", "jewellery": "jewellery", "ornament": "jewellery", "gold": "jewellery",

        # Choreographer-related
        "choreographer": "choreographer", "choreography": "choreographer", "dance": "choreographer",

        # Miscellaneous
        "planner": "other", "coordinator": "other", "consultant": "other", "other services": "other", "gift": "other"
    }
    
    @staticmethod
    def normalize_vendor_type(vt):
        import re
        if not vt:
            return 'other'

        # Step 1: Clean text
        vt = vt.strip().lower()
        vt = re.sub(r'[^a-z\s&]', '', vt).strip()

        # Step 2: Direct match or plural reduction
        if vt in VendorCategories.TYPE_MAP:
            return VendorCategories.TYPE_MAP[vt]
        if vt.endswith('s') and vt[:-1] in VendorCategories.TYPE_MAP:
            return VendorCategories.TYPE_MAP[vt[:-1]]

        # Step 3: Partial keyword search (for robustness)
        for key, value in VendorCategories.TYPE_MAP.items():
            if key in vt:
                return value

        return 'other'
    
    @staticmethod
    def get_category_display_info(category):
        """Get display information for a category"""
        return VendorCategories.CATEGORIES.get(category, VendorCategories.CATEGORIES['other'])