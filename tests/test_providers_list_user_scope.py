from types import SimpleNamespace

import app.api.routes.providers as provider_routes


def test_list_user_providers_filters_out_foreign_records(monkeypatch) -> None:
    own_provider = SimpleNamespace(id=10, name="Own Provider")
    foreign_provider = SimpleNamespace(id=11, name="Foreign Provider")

    class DummyProviderRepository:
        def __init__(self, db):
            self.db = db

        def list_for_user(self, user_id: int):
            assert user_id == 123
            return [own_provider, foreign_provider]

        def get_for_user(self, provider_id: int, user_id: int):
            assert user_id == 123
            if provider_id == own_provider.id:
                return own_provider
            return None

    monkeypatch.setattr(
        provider_routes,
        "ProviderRepository",
        DummyProviderRepository,
    )

    response = provider_routes.list_user_providers(
        db=object(),
        current_user=SimpleNamespace(id=123),
    )

    assert response == [own_provider]


def test_list_user_providers_rejects_missing_user_id() -> None:
    try:
        provider_routes.list_user_providers(
            db=object(),
            current_user=SimpleNamespace(id=None),
        )
        raise AssertionError("Expected HTTPException")
    except Exception as exc:
        assert exc.status_code == 401
        assert exc.detail == "Unauthorized"
