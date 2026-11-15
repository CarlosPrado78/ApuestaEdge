"""Registro directo /?registro: el diálogo de alta se abre sin clics previos.

La URL `/?registro` (o `/?register`) se comparte en la invitación a
testers: abre `#login-dialog` ya en modo "Crear una". Aquí se cubre que
la página sirva el diálogo, que app.js consuma el parámetro (refrescar
no lo reabra), que cambie a modo registro con i18n ES/EN y que no se
abra si ya hay sesión.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_home_serves_login_dialog_elements(client):
    html = client.get("/").text
    assert 'id="btn-login"' in html
    assert 'id="login-dialog"' in html
    assert 'id="login-toggle"' in html


def test_app_js_has_register_from_url_flow(client):
    js = client.get("/app.js").text
    # Función y binding.
    assert "function openRegisterFromUrl()" in js
    assert "openRegisterFromUrl();" in js
    # Acepta el parámetro en ES y EN.
    assert 'params.has("registro")' in js
    assert 'params.has("register")' in js
    # Conmuta a modo registro y pinta los textos del diálogo.
    assert 'loginMode = "register"' in js
    assert "updateLoginDialogText();" in js
    assert "openLogin();" in js


def test_app_js_consumes_param_and_guards_session(client):
    js = client.get("/app.js").text
    # El parámetro se borra de la URL: refrescar no reabre el diálogo.
    assert 'params.delete("registro")' in js
    assert 'params.delete("register")' in js
    assert "history.replaceState" in js
    # Con sesión iniciada no se ofrece crear cuenta.
    assert 'localStorage.getItem("ae_token")' in js


def test_register_mode_texts_exist_in_es_and_en(client):
    js = client.get("/app.js").text
    for key in ("create_account_title", "login_help_register",
                "btn_register_submit", "login_toggle_back"):
        # Cada clave debe estar definida en el bloque ES y en el EN.
        assert js.count(f"{key}:") >= 2, f"falta i18n de {key}"


def test_register_url_param_not_declared_twice(client):
    """openRegisterFromUrl se define y se llama una sola vez (sin doble
    binding que abriera el diálogo dos veces)."""
    js = client.get("/app.js").text
    assert js.count("function openRegisterFromUrl()") == 1
    assert js.count("openRegisterFromUrl();") == 1
