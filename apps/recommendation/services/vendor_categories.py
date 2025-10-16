class VendorCategories:
    CATEGORIES = {
        'photographer': {'display_name': 'Photography', 'description': 'Capture memories', 'icon': '📸', 'priority': 1},
        'caterer': {'display_name': 'Catering', 'description': 'Delicious food', 'icon': '🍽️', 'priority': 2},
        'decorator': {'display_name': 'Decorators', 'description': 'Beautiful setups', 'icon': '🎨', 'priority': 3},
        'dj': {'display_name': 'DJ & Music', 'description': 'Keep the party going', 'icon': '🎵', 'priority': 4},
        'videographer': {'display_name': 'Videography', 'description': 'Wedding films', 'icon': '🎥', 'priority': 5},
        'makeup_artist': {'display_name': 'Makeup', 'description': 'Look your best', 'icon': '💄', 'priority': 6},
        'mehendi_artist': {'display_name': 'Mehendi', 'description': 'Henna designs', 'icon': '🤚', 'priority': 7},
        'band': {'display_name': 'Live Band', 'description': 'Live music', 'icon': '🎸', 'priority': 8},
        'transport': {'display_name': 'Transport', 'description': 'Arrive in style', 'icon': '🚗', 'priority': 9},
        'pandit': {'display_name': 'Pandits', 'description': 'Sacred guidance', 'icon': '🙏', 'priority': 10},
        'invitation_designer': {'display_name': 'Invitations', 'description': 'Wedding invites', 'icon': '💌', 'priority': 11},
        'jewellery': {'display_name': 'Jewellery', 'description': 'Wedding jewellery', 'icon': '💎', 'priority': 12},
        'choreographer': {'display_name': 'Choreographers', 'description': 'Dance prep', 'icon': '💃', 'priority': 13},
        'other': {'display_name': 'Other', 'description': 'Misc services', 'icon': '⭐', 'priority': 99}
    }

    TYPE_MAP = {
        "photography": "photographer", "photo": "photographer",
        "catering": "caterer", "food": "caterer",
        "decoration": "decorator", "decor": "decorator",
        "music": "dj", "dj": "dj",
        "videography": "videographer", "video": "videographer",
        "makeup": "makeup_artist",
        "mehendi": "mehendi_artist", "henna": "mehendi_artist",
        "band": "band",
        "transport": "transport", "car": "transport",
        "priest": "pandit", "pandit": "pandit",
        "invitation": "invitation_designer", "card": "invitation_designer",
        "jewel": "jewellery",
        "dance": "choreographer", "choreography": "choreographer"
    }

    @staticmethod
    def normalize_vendor_type(vendor_type):
        if not vendor_type:
            return "other"
        vendor_type = vendor_type.lower().strip()
        if vendor_type in VendorCategories.CATEGORIES:
            return vendor_type
        for k, v in VendorCategories.TYPE_MAP.items():
            if k in vendor_type:
                return v
        return "other"

    @staticmethod
    def get_category_display_info(category):
        return VendorCategories.CATEGORIES.get(category, VendorCategories.CATEGORIES['other'])
