import json
import os
from datetime import datetime

class UserProfileStore:
    def __init__(self, profiles_dir: str = "data/profiles"):
        self.profiles_dir = profiles_dir
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)

    def get_profile(self, user_id: str) -> dict or None:
        file_path = os.path.join(self.profiles_dir, f"{user_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None

    def save_profile(self, user_id: str, profile: dict):
        file_path = os.path.join(self.profiles_dir, f"{user_id}.json")
        profile['last_interaction'] = datetime.now().isoformat()
        with open(file_path, 'w') as f:
            json.dump(profile, f, indent=2)

    def get_or_create(self, user_id: str) -> dict:
        profile = self.get_profile(user_id)
        if not profile:
            profile = {
                "user_id": user_id,
                "experience_level": "unknown",
                "preferred_detail_level": "verbose",
                "preferred_review_mode": "full-walkthrough",
                "profiling_complete": False,
                "session_count": 0,
                "portfolio_segments": [],
                "created_at": datetime.now().isoformat(),
                "last_interaction": datetime.now().isoformat()
            }
            self.save_profile(user_id, profile)
        return profile

    def update_from_profiling(self, user_id: str, profiling_result: dict):
        profile = self.get_or_create(user_id)
        profile.update(profiling_result)
        profile['session_count'] += 1
        profile['profiling_complete'] = True
        self.save_profile(user_id, profile)
        return profile
