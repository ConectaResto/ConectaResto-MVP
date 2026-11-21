"""Shared model infrastructure and SQLAlchemy registration."""


def register_models():
    """Import each domain's models so SQLAlchemy can resolve all mappings."""
    import app.catalog.models  # noqa: F401
    import app.mesas.models  # noqa: F401
    import app.pedidos.models  # noqa: F401
    import app.servicios.models  # noqa: F401
    import app.users.models  # noqa: F401
