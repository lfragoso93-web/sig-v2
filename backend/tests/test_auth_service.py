"""Testes para auth_service — hash e verificação de senhas."""
import pytest
from app.services.auth_service import hash_password, verify_password, create_access_token
from jose import jwt
from app.core.config import settings


class TestPasswordHash:

    def test_hash_diferente_do_plain(self):
        plain = "senha123"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_verify_senha_correta(self):
        plain = "senha123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_senha_errada(self):
        hashed = hash_password("correta")
        assert verify_password("errada", hashed) is False

    def test_hash_deterministico_falso(self):
        """Bcrypt gera salt diferente a cada chamada — dois hashes distintos."""
        plain = "senha"
        assert hash_password(plain) != hash_password(plain)

    def test_verify_string_vazia(self):
        hashed = hash_password("abc")
        assert verify_password("", hashed) is False


class TestCreateAccessToken:

    def test_token_decodificavel(self):
        token = create_access_token({"sub": "42"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "42"

    def test_token_contem_exp(self):
        token = create_access_token({"sub": "1"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_token_distinto_para_dados_distintos(self):
        t1 = create_access_token({"sub": "1"})
        t2 = create_access_token({"sub": "2"})
        assert t1 != t2
