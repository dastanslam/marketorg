from django.http import Http404
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import DisallowedHost

from .models import Store


class StoreSubdomainMiddleware(MiddlewareMixin):
    """
    Определяет магазин по поддомену и кладёт в request.store

    Пример:
      shop1.example.com -> subdomain = "shop1"
      example.com       -> subdomain = None (главный сайт)
    """

    def process_request(self, request):
        request.store = None

        try:
            host = request.get_host()  # может быть "shop1.example.com:8000"
        except DisallowedHost:
            return None

        # убираем порт
        host = host.split(":")[0].lower().strip(".")

        base_domain = getattr(settings, "BASE_DOMAIN", None)  # например: "example.com"
        ignored = set(getattr(settings, "SUBDOMAIN_IGNORED", ["www"]))
        bypass_prefixes = tuple(getattr(settings, "SUBDOMAIN_BYPASS_PREFIXES", ["api", "admin"]))

        # Если admin/api на отдельном поддомене — пропускаем
        if host.split(".")[0] in bypass_prefixes:
            return None

        subdomain = None

        # Вариант А (рекомендую): ты задаёшь BASE_DOMAIN
        if base_domain:
            base_domain = base_domain.lower().strip(".")
            if host == base_domain:
                subdomain = None
            elif host.endswith("." + base_domain):
                subdomain = host[: -(len(base_domain) + 1)]  # всё слева от .base_domain
            else:
                # запрос не на наш домен
                return None

        # Вариант B: без BASE_DOMAIN (менее надёжно) — берём первый лейбл если их >= 3
        else:
            parts = host.split(".")
            if len(parts) >= 3:
                subdomain = parts[0]

        if not subdomain or subdomain in ignored:
            return None

        store = Store.objects.filter(
            subdomain=subdomain,
            is_active=True,
        ).first()

        if not store:
            raise Http404("Магазин не найден")

        # по желанию: если есть поле is_blocked
        if hasattr(store, "is_blocked") and store.is_blocked:
            raise Http404("Магазин недоступен")

        request.store = store
        return None
