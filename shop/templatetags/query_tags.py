from django import template

register = template.Library()

@register.simple_tag
def qs_remove(request, key, value=None):
    q = request.GET.copy()

    if value is None:
        q.pop(key, None)
    else:
        value = str(value)
        vals = [v for v in q.getlist(key) if v != value]
        if vals:
            q.setlist(key, vals)
        else:
            q.pop(key, None)

    query = q.urlencode()
    base = request.path  # /shop/

    return f"{base}?{query}" if query else base

@register.simple_tag
def qs_set(request, key, value):
    """
    Добавляет или изменяет параметр в query string
    пример:
    ?category=1&size=M -> ?category=1&size=M&sort=price_desc
    """

    q = request.GET.copy()

    if value:
        q[key] = value
    else:
        q.pop(key, None)

    query = q.urlencode()

    base = request.path
    return f"{base}?{query}" if query else base