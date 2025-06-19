def make_query_string(prefix: str, values: list[str]) -> str:
    """Converts a list of values to a query string for the card browser"""
    if not prefix or not values:
        return ""
    query = "("
    for i, value in enumerate(values):
        query += f'"{prefix}:{value}"'
        if i < len(values) - 1:
            query += " OR "
    query += ")"
    return query
