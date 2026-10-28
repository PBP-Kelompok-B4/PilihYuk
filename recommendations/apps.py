from django.apps import AppConfig


class RecommendationsConfig(AppConfig):
    name = "recommendations"
    # Keep the existing migration history under its original app label.
    label = "substitutions"
