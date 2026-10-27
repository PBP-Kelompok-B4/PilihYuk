# Rename the former substitutions app models while preserving existing migration history.

from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("substitutions", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Substitution",
            new_name="Recommendation",
        ),
        migrations.RenameModel(
            old_name="SubstitutionVote",
            new_name="RecommendationVote",
        ),
        migrations.RemoveConstraint(
            model_name="recommendation",
            name="unique_substitution_direction",
        ),
        migrations.RemoveConstraint(
            model_name="recommendation",
            name="different_substitution_products",
        ),
        migrations.RemoveConstraint(
            model_name="recommendationvote",
            name="one_vote_per_user_per_substitution",
        ),
        migrations.RemoveConstraint(
            model_name="recommendationvote",
            name="substitution_vote_is_agree_or_disagree",
        ),
        migrations.RenameField(
            model_name="recommendationvote",
            old_name="substitution",
            new_name="recommendation",
        ),
        migrations.AlterField(
            model_name="recommendation",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="recommendations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="recommendation",
            name="replacement_product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="incoming_recommendations",
                to="product_catalog.product",
            ),
        ),
        migrations.AlterField(
            model_name="recommendation",
            name="source_product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="outgoing_recommendations",
                to="product_catalog.product",
            ),
        ),
        migrations.AlterField(
            model_name="recommendationvote",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="recommendation_votes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelTable(
            name="recommendation",
            table="recommendations_recommendation",
        ),
        migrations.AlterModelTable(
            name="recommendationvote",
            table="recommendations_recommendation_vote",
        ),
        migrations.AddConstraint(
            model_name="recommendation",
            constraint=models.UniqueConstraint(
                fields=("source_product", "replacement_product"),
                name="unique_recommendation_direction",
            ),
        ),
        migrations.AddConstraint(
            model_name="recommendation",
            constraint=models.CheckConstraint(
                condition=~models.Q(source_product=models.F("replacement_product")),
                name="different_recommendation_products",
            ),
        ),
        migrations.AddConstraint(
            model_name="recommendationvote",
            constraint=models.UniqueConstraint(
                fields=("recommendation", "user"),
                name="one_vote_per_user_per_recommendation",
            ),
        ),
        migrations.AddConstraint(
            model_name="recommendationvote",
            constraint=models.CheckConstraint(
                condition=models.Q(value__in=[1, -1]),
                name="recommendation_vote_is_agree_or_disagree",
            ),
        ),
    ]
