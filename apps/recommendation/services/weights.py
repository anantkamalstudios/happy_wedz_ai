class RecommendationWeights:
    INTERACTION_WEIGHTS = {
        'like': 5.0,
        'bookmark': 4.0,
        'view': 1.5,
        'skip': -0.5
    }

    TIME_DECAY_DAYS = {
        1: 1.0,
        7: 0.9,
        30: 0.7,
        90: 0.5,
        365: 0.2
    }

    ALGORITHM_WEIGHTS = {
        'session_based': 0.35,
        'user_preference': 0.30,
        'collaborative': 0.20,
        'popularity': 0.10,
        'diversity': 0.05
    }
