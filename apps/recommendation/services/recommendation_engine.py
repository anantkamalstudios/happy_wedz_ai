from datetime import datetime
from apps.recommendation.services.cache import venues_cache, vendors_cache, user_interaction_cache
from apps.recommendation.services.weights import RecommendationWeights
from apps.recommendation.models.user import UserFetch

class HybridRecommendationEngine:
    """Main hybrid recommendation engine"""

    @staticmethod
    def get_recommendations(user_id, limit=12):
        user = UserFetch.query.get(user_id)
        if not user:
            return []

        days_since_registration = (datetime.utcnow() - user.created_at).days
        interactions = user_interaction_cache.get(user_id, {}).get('interactions', [])
        is_new_user = days_since_registration <= 7 and len(interactions) < 5

        if is_new_user:
            return HybridRecommendationEngine.new_user_recommendations(user.city, limit)

        # otherwise just return popular vendors + venues
        recs = list(venues_cache.values())[:limit//2] + list(vendors_cache.values())[:limit//2]
        return recs

    @staticmethod
    def new_user_recommendations(user_city, limit=10):
        recs = []
        city_venues = [v for v in venues_cache.values() if v['city'] == user_city]
        city_vendors = [v for v in vendors_cache.values() if v['city'] == user_city]
        recs.extend(sorted(city_venues, key=lambda x: x.get('rating', 0), reverse=True)[:limit//2])
        recs.extend(sorted(city_vendors, key=lambda x: x.get('rating', 0), reverse=True)[:limit//2])
        return recs

def get_fallback_recommendations(user_id):
    user = User.query.get(user_id)
    user_city = user.city if user else None
    venues = sorted(list(venues_cache.values()), key=lambda x: x.get('rating', 0), reverse=True)[:10]
    vendors = [v for v in vendors_cache.values() if not user_city or v['city'] == user_city][:10]
    return {"method": "fallback", "venues": venues, "vendors": vendors}

class UserPreferenceRecommender:
    @staticmethod
    def calculate_weighted_preferences(interactions):
        from collections import defaultdict
        cities = defaultdict(int)
        vendor_categories = defaultdict(int)
        types = defaultdict(int)
        for interaction in interactions:
            weight = RecommendationWeights.INTERACTION_WEIGHTS.get(interaction.get('interaction_type'), 1)
            # Assuming interaction has 'city' and 'category', but if not, use 'unknown'
            cities[interaction.get('city', 'unknown')] += weight
            vendor_categories[interaction.get('category', 'unknown')] += weight
            types[interaction.get('item_type', 'unknown')] += weight
        return {
            'cities': cities,
            'vendor_categories': vendor_categories,
            'types': types
        }
