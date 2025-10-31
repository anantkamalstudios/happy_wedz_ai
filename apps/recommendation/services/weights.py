class RecommendationWeights:
    # Interaction weights (how much each action shows user interest)
    INTERACTION_WEIGHTS = {
        'like': 5.0,      # Highest weight - user explicitly liked
        'bookmark': 4.0,   # High weight - user wants to save
        'view': 3.0,      # Medium weight - user showed interest
        'skip': -0.5      # Negative weight - user not interested
    }
    
    # Time decay weights (recent interactions matter more)
    TIME_DECAY_DAYS = {
        1: 1.0,      # Today - full weight
        7: 0.9,      # Last week - 90% weight
        30: 0.7,     # Last month - 70% weight
        90: 0.5,     # Last 3 months - 50% weight
        365: 0.2     # Last year - 20% weight
    }
    
    # Content similarity weights
    SIMILARITY_WEIGHTS = {
        'same_city': 3.0,
        'nearby_city': 1.5,
        'same_type': 2.5,
        'same_price_range': 2.0,
        'same_capacity_range': 1.8,
        'similar_rating': 1.5
    }
    
    # Algorithm combination weights
    ALGORITHM_WEIGHTS = {
        'session_based': 0.35,      # Based on current session
        'user_preference': 0.30,    # Based on historical preferences
        'collaborative': 0.20,      # Based on similar users
        'popularity': 0.10,         # Based on overall popularity
        'diversity': 0.05          # For recommendation diversity
    }