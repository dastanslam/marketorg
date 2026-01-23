from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count

from .models import ProductReview, Product


def recalc_product_rating(product_id: int):
    qs = ProductReview.objects.filter(product_id=product_id, is_published=True)
    agg = qs.aggregate(avg=Avg("rating"), cnt=Count("id"))

    avg = agg["avg"] or 0
    cnt = agg["cnt"] or 0

    Product.objects.filter(id=product_id).update(
        rating_avg=avg,
        rating_count=cnt
    )


@receiver(post_save, sender=ProductReview)
def review_saved(sender, instance, **kwargs):
    recalc_product_rating(instance.product_id)


@receiver(post_delete, sender=ProductReview)
def review_deleted(sender, instance, **kwargs):
    recalc_product_rating(instance.product_id)
