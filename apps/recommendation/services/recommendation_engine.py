from collections import defaultdict
from datetime import datetime, timedelta
from apps.recommendation.services.cache import venues_cache, vendors_cache, user_interaction_cache, vendor_categories_cache
from apps.recommendation.services.weights import RecommendationWeights
from apps.recommendation.services.vendor_categories import VendorCategories
from apps.recommendation.models.user import User

class SessionBasedRecommender:
    """Recommend based on current session interactions"""
    
    @staticmethod
    def get_recommendations(user_id, session_interactions, limit=10):
        if not session_interactions:
            return []
        
        recommendations = []
        session_cities = []
        session_venues = []
        
        # Analyze session patterns
        for interaction in session_interactions[-10:]:
            item_id = interaction['item_id']
            item_type = interaction['item_type']
            interaction_type = interaction['interaction_type']
            
            if item_type == 'venue' and item_id in venues_cache:
                venue = venues_cache[item_id]
                session_cities.append(venue['city'])
                session_venues.append(item_id)
                
                if interaction_type in ['like', 'bookmark']:
                    from .vendor_matcher import VendorMatcher
                    vendor_recs = VendorMatcher.get_vendors_for_venue_city(venue['city'], limit=5)
                    for vendor in vendor_recs:
                        vendor['source'] = 'session_venue_match'
                        vendor['score'] = RecommendationWeights.INTERACTION_WEIGHTS[interaction_type] * 0.8
                        recommendations.append(vendor)
        
        # Recommend more venues in preferred cities
        if session_cities:
            from collections import Counter
            city_counter = Counter(session_cities)
            preferred_city = city_counter.most_common(1)[0][0]
            
            venue_recs = SessionBasedRecommender.get_similar_venues(
                preferred_city, session_venues, limit=5
            )
            recommendations.extend(venue_recs)
        
        return sorted(recommendations, key=lambda x: x.get('score', 0), reverse=True)[:limit]
    
    @staticmethod
    def get_similar_venues(city, exclude_venues, limit=5):
        similar_venues = []
        for venue_id, venue in venues_cache.items():
            if venue_id not in exclude_venues and venue['city'] == city:
                venue_copy = venue.copy()
                venue_copy['source'] = 'session_city_match'
                venue_copy['score'] = venue['rating'] * 1.2
                similar_venues.append(venue_copy)
        
        return sorted(similar_venues, key=lambda x: x['score'], reverse=True)[:limit]

class UserPreferenceRecommender:
    """Recommend based on historical user preferences with decay"""
    
    @staticmethod
    def get_recommendations(user_id, limit=10):
        if user_id not in user_interaction_cache:
            return []
        
        interactions = user_interaction_cache[user_id]['interactions']
        if not interactions:
            return []
        
        preferences = UserPreferenceRecommender.calculate_weighted_preferences(interactions)
        recommendations = []
        
        venue_recs = UserPreferenceRecommender.get_preference_based_venues(preferences, limit//2)
        recommendations.extend(venue_recs)
        
        vendor_recs = UserPreferenceRecommender.get_preference_based_vendors(preferences, limit//2)
        recommendations.extend(vendor_recs)
        
        return sorted(recommendations, key=lambda x: x.get('score', 0), reverse=True)[:limit]

    @staticmethod
    def calculate_weighted_preferences(interactions):
        preferences = {
            'cities': defaultdict(float),
            'types': defaultdict(float),
            'vendor_categories': defaultdict(float),
            'price_ranges': [],
            'capacity_ranges': [],
            'ratings': [],
            'interacted_items': set()
        }
        
        for interaction in interactions:
            item_id = interaction['item_id']
            item_type = interaction['item_type']
            interaction_type = interaction['interaction_type']
            days_ago = interaction['days_ago']
            
            time_weight = UserPreferenceRecommender.get_time_decay_weight(days_ago)
            interaction_weight = RecommendationWeights.INTERACTION_WEIGHTS.get(interaction_type, 1.0)
            total_weight = time_weight * interaction_weight
            
            preferences['interacted_items'].add(item_id)
            
            if interaction_weight > 0:
                if item_type == 'venue' and item_id in venues_cache:
                    venue = venues_cache[item_id]
                    preferences['cities'][venue['city']] += total_weight
                    preferences['types']['venue'] += total_weight
                    
                    if venue['price'] > 0:
                        preferences['price_ranges'].append(venue['price'])
                    if venue['capacity'] > 0:
                        preferences['capacity_ranges'].append(venue['capacity'])
                    preferences['ratings'].append(venue['rating'])
                
                elif item_type == 'vendor' and item_id in vendors_cache:
                    vendor = vendors_cache[item_id]
                    preferences['cities'][vendor['city']] += total_weight
                    preferences['types']['vendor'] += total_weight
                    preferences['vendor_categories'][vendor['category']] += total_weight
                    preferences['ratings'].append(vendor['rating'])
        
        return preferences

    @staticmethod
    def get_time_decay_weight(days_ago):
        for days, weight in RecommendationWeights.TIME_DECAY_DAYS.items():
            if days_ago <= days:
                return weight
        return 0.1

class CollaborativeRecommender:
    """Recommend based on users with similar interaction patterns"""
    
    @staticmethod
    def get_recommendations(user_id, limit=10):
        if user_id not in user_interaction_cache:
            return []
        
        similar_users = CollaborativeRecommender.find_similar_users(user_id)
        if not similar_users:
            return []
        
        recommendations = []
        current_user_items = set()
        
        for interaction in user_interaction_cache[user_id]['interactions']:
            current_user_items.add(interaction['item_id'])
        
        item_scores = defaultdict(float)
        for similar_user, similarity in similar_users[:5]:
            for interaction in user_interaction_cache[similar_user]['interactions']:
                if interaction['item_id'] not in current_user_items:
                    weight = RecommendationWeights.INTERACTION_WEIGHTS.get(interaction['interaction_type'], 1.0)
                    if weight > 0:
                        item_scores[interaction['item_id']] += weight * similarity
        
        for item_id, score in sorted(item_scores.items(), key=lambda x: x[1], reverse=True)[:limit]:
            item_data = None
            if item_id in venues_cache:
                item_data = venues_cache[item_id].copy()
            elif item_id in vendors_cache:
                item_data = vendors_cache[item_id].copy()
            
            if item_data:
                item_data['source'] = 'collaborative'
                item_data['score'] = score
                recommendations.append(item_data)
        
        return recommendations
    
    @staticmethod
    def find_similar_users(user_id):
        current_user_interactions = user_interaction_cache[user_id]['interactions']
        current_user_items = set(i['item_id'] for i in current_user_interactions)
        
        similarities = []
        for other_user_id in user_interaction_cache:
            if other_user_id == user_id:
                continue
            
            other_interactions = user_interaction_cache[other_user_id]['interactions']
            other_user_items = set(i['item_id'] for i in other_interactions)
            
            intersection = len(current_user_items & other_user_items)
            union = len(current_user_items | other_user_items)
            
            if union > 0:
                similarity = intersection / union
                if similarity > 0.1:
                    similarities.append((other_user_id, similarity))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)

class PopularityRecommender:
    """Recommend popular items with location and user context"""
    
    @staticmethod
    def get_recommendations(user_city, user_budget=None, limit=10):
        recommendations = []
        
        venue_recs = PopularityRecommender.get_popular_venues(user_city, user_budget, limit//2)
        recommendations.extend(venue_recs)
        
        vendor_recs = PopularityRecommender.get_popular_vendors(user_city, limit//2)
        recommendations.extend(vendor_recs)
        
        return recommendations
    
    @staticmethod
    def get_popular_venues(user_city, user_budget, limit):
        scored_venues = []
        
        for venue_id, venue in venues_cache.items():
            score = venue['rating']
            
            if venue['city'] == user_city:
                score *= 1.5
            
            if user_budget and venue['price'] > 0:
                if venue['price'] <= user_budget:
                    score *= 1.2
                elif venue['price'] > user_budget * 1.5:
                    score *= 0.5
            
            venue_copy = venue.copy()
            venue_copy['source'] = 'popularity'
            venue_copy['score'] = score
            scored_venues.append(venue_copy)
        
        return sorted(scored_venues, key=lambda x: x['score'], reverse=True)[:limit]
    
    @staticmethod
    def get_popular_vendors(user_city, limit):
        scored_vendors = []
        
        for vendor_id, vendor in vendors_cache.items():
            score = vendor['rating']
            
            if vendor['city'] == user_city:
                score *= 1.3
            
            vendor_copy = vendor.copy()
            vendor_copy['source'] = 'popularity'
            vendor_copy['score'] = score
            scored_vendors.append(vendor_copy)
        
        return sorted(scored_vendors, key=lambda x: x['score'], reverse=True)[:limit]

class NewUserRecommender:
    """Special recommendations for new users based on their registration city"""
    
    @staticmethod
    def get_recommendations(user_city, user_budget=None, limit=12):
        recommendations = []
        
        city_venues = []
        other_venues = []
        
        for venue_id, venue in venues_cache.items():
            venue_copy = venue.copy()
            venue_copy['source'] = 'new_user_city'
            
            if venue['city'] == user_city:
                venue_copy['score'] = venue['rating'] * 2.0
                city_venues.append(venue_copy)
            else:
                venue_copy['score'] = venue['rating']
                other_venues.append(venue_copy)
        
        city_venues.sort(key=lambda x: x['score'], reverse=True)
        recommendations.extend(city_venues[:6])
        
        if len(recommendations) < limit//2:
            other_venues.sort(key=lambda x: x['score'], reverse=True)
            recommendations.extend(other_venues[:limit//2 - len(recommendations)])
        
        city_vendors = []
        for vendor_id, vendor in vendors_cache.items():
            if vendor['city'] == user_city:
                vendor_copy = vendor.copy()
                vendor_copy['source'] = 'new_user_city'
                vendor_copy['score'] = vendor['rating'] * 1.8
                city_vendors.append(vendor_copy)
        
        city_vendors.sort(key=lambda x: x['score'], reverse=True)
        recommendations.extend(city_vendors[:limit//2])
        
        return recommendations[:limit]

class CategorizedVendorRecommender:
    """Generate vendor recommendations organized by categories"""
    
    @staticmethod
    def get_categorized_recommendations(user_id, vendors_per_category=3):
        user = User.query.get(user_id)
        if not user:
            return {}
        
        user_interactions = user_interaction_cache.get(user_id, {}).get('interactions', [])
        
        if user_interactions:
            preferences = UserPreferenceRecommender.calculate_weighted_preferences(user_interactions)
        else:
            preferences = {'cities': {user.city: 1.0}, 'vendor_categories': {}, 'interacted_items': set()}
        
        categorized_recs = {}
        
        sorted_categories = sorted(
            vendor_categories_cache.keys(), 
            key=lambda cat: (
                -preferences['vendor_categories'].get(cat, 0),
                VendorCategories.get_category_display_info(cat)['priority']
            )
        )
        
        for category in sorted_categories:
            if category not in vendor_categories_cache:
                continue
            
            category_vendors = vendor_categories_cache[category]
            category_info = VendorCategories.get_category_display_info(category)
            
            scored_vendors = []
            for vendor in category_vendors:
                if vendor['id'] in preferences['interacted_items']:
                    continue
                
                score = vendor['rating']
                
                if vendor['city'] in preferences['cities']:
                    score += preferences['cities'][vendor['city']] * 0.5
                
                if vendor['city'] == user.city:
                    score *= 1.3
                
                if category in preferences['vendor_categories']:
                    score += preferences['vendor_categories'][category] * 0.3
                
                vendor_copy = vendor.copy()
                vendor_copy['score'] = score
                scored_vendors.append(vendor_copy)
            
            scored_vendors.sort(key=lambda x: x['score'], reverse=True)
            top_vendors = scored_vendors[:vendors_per_category]
            
            if top_vendors:
                categorized_recs[category] = {
                    'category': category,
                    'display_name': category_info['display_name'],
                    'description': category_info['description'],
                    'priority': category_info['priority'],
                    'vendors': top_vendors,
                    'total_available': len(category_vendors),
                    'user_preference_score': preferences['vendor_categories'].get(category, 0)
                }
        
        return categorized_recs

class HybridRecommendationEngine:
    """Main engine that combines all recommendation algorithms"""
    
    @staticmethod
    def get_recommendations(user_id, limit=12):
        user = User.query.get(user_id)
        if not user:
            return []
        
        days_since_registration = (datetime.utcnow() - user.created_at).days
        user_interactions = user_interaction_cache.get(user_id, {}).get('interactions', [])
        is_new_user = days_since_registration <= 7 and len(user_interactions) < 5
        
        if is_new_user:
            print(f"New user detected: {user_id}, providing city-based recommendations")
            return NewUserRecommender.get_recommendations(user.city, user.overall_budget, limit)
        
        all_recommendations = []
        seen_items = set()
        
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        session_interactions = [
            i for i in user_interactions 
            if i['timestamp'] >= recent_cutoff
        ]
        
        session_recs = SessionBasedRecommender.get_recommendations(
            user_id, session_interactions, int(limit * 0.35)
        )
        HybridRecommendationEngine.add_unique_recommendations(
            all_recommendations, session_recs, seen_items, 0.35
        )
        
        preference_recs = UserPreferenceRecommender.get_recommendations(
            user_id, int(limit * 0.30)
        )
        HybridRecommendationEngine.add_unique_recommendations(
            all_recommendations, preference_recs, seen_items, 0.30
        )
        
        collaborative_recs = CollaborativeRecommender.get_recommendations(
            user_id, int(limit * 0.20)
        )
        HybridRecommendationEngine.add_unique_recommendations(
            all_recommendations, collaborative_recs, seen_items, 0.20
        )
        
        remaining_slots = limit - len(all_recommendations)
        if remaining_slots > 0:
            popularity_recs = PopularityRecommender.get_recommendations(
                user.city, user.overall_budget, remaining_slots
            )
            HybridRecommendationEngine.add_unique_recommendations(
                all_recommendations, popularity_recs, seen_items, 0.15
            )
        
        all_recommendations.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        return all_recommendations[:limit]
    
    @staticmethod
    def add_unique_recommendations(all_recs, new_recs, seen_items, weight):
        for rec in new_recs:
            item_id = rec.get('id')
            item_type = rec.get('item_type') or ('venue' if rec.get('type') == 'venue' else 'vendor')
            item_key = (item_type, item_id)
            if item_key not in seen_items:
                rec['final_score'] = rec.get('score', 0) * weight
                all_recs.append(rec)
                seen_items.add(item_key)