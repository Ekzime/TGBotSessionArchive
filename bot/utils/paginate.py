import math


def paginate(items, page, size):
    total_pages = math.ceil(len(items) / size)
    if page < 1 or page > total_pages:
        return None, total_pages
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    return items[start_idx:end_idx], total_pages
