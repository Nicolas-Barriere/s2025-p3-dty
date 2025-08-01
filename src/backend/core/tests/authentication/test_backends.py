"""Unit tests for the Authentication Backends."""

import random
import re
from logging import Logger
from unittest import mock

from django.core.exceptions import SuspiciousOperation
from django.test.utils import override_settings

import pytest
import responses

from core import models
from core.authentication.backends import OIDCAuthenticationBackend
from core.factories import UserFactory

pytestmark = pytest.mark.django_db


@override_settings(MESSAGES_TESTDOMAIN=None)
def test_authentication_getter_existing_user_no_email(monkeypatch):
    """
    If an existing user matches the user's info sub, the user should be returned.
    """

    klass = OIDCAuthenticationBackend()
    db_user = UserFactory()

    def get_userinfo_mocked(*args):
        return {"sub": db_user.sub}

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert user == db_user


@override_settings(MESSAGES_TESTDOMAIN=None)
def test_authentication_getter_existing_user_via_email(monkeypatch):
    """
    If an existing user doesn't match the sub but matches the email,
    the user should be returned.
    """

    klass = OIDCAuthenticationBackend()
    db_user = UserFactory()

    def get_userinfo_mocked(*args):
        return {"sub": "123", "email": db_user.email}

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert user == db_user


def test_authentication_getter_email_none(monkeypatch):
    """
    If no user is found with the sub and no email is provided, no user should be created (we need emails here!)
    """

    klass = OIDCAuthenticationBackend()
    UserFactory(email=None)

    def get_userinfo_mocked(*args):
        user_info = {"sub": "123"}
        if random.choice([True, False]):
            user_info["email"] = None
        return user_info

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    # Since the sub and email didn't match, it shouldn't create a new user
    assert models.User.objects.count() == 1
    assert user is None


@override_settings(MESSAGES_TESTDOMAIN=None)
def test_authentication_getter_existing_user_with_email(monkeypatch):
    """
    When the user's info contains an email and targets an existing user,
    """
    klass = OIDCAuthenticationBackend()
    user = UserFactory(full_name="John Doe")

    def get_userinfo_mocked(*args):
        return {
            "sub": user.sub,
            "email": user.email,
            "first_name": "John",
            "last_name": "Doe",
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    authenticated_user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert user == authenticated_user


@override_settings(MESSAGES_TESTDOMAIN=None)
@pytest.mark.parametrize(
    "first_name, last_name, email",
    [
        ("Jack", "Doe", "john.doe@example.com"),
        ("John", "Duy", "john.doe@example.com"),
        ("John", "Doe", "jack.duy@example.com"),
        ("Jack", "Duy", "jack.duy@example.com"),
    ],
)
def test_authentication_getter_existing_user_change_fields_sub(
    first_name, last_name, email, monkeypatch
):
    """
    It should update the email or name fields on the user when they change
    and the user was identified by its "sub".
    """
    klass = OIDCAuthenticationBackend()
    user = UserFactory(full_name="John Doe", email="john.doe@example.com")

    def get_userinfo_mocked(*args):
        return {
            "sub": user.sub,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    authenticated_user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert user == authenticated_user
    user.refresh_from_db()
    assert user.email == email
    assert user.full_name == f"{first_name:s} {last_name:s}"


@override_settings(MESSAGES_TESTDOMAIN=None)
@pytest.mark.parametrize(
    "first_name, last_name, email",
    [
        ("Jack", "Doe", "john.doe@example.com"),
        ("John", "Duy", "john.doe@example.com"),
    ],
)
def test_authentication_getter_existing_user_change_fields_email(
    first_name, last_name, email, monkeypatch
):
    """
    It should update the name fields on the user when they change
    and the user was identified by its "email" as fallback.
    """
    klass = OIDCAuthenticationBackend()
    user = UserFactory(full_name="John Doe", email="john.doe@example.com")

    def get_userinfo_mocked(*args):
        return {
            "sub": "123",
            "email": user.email,
            "first_name": first_name,
            "last_name": last_name,
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    authenticated_user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert user == authenticated_user
    user.refresh_from_db()
    assert user.email == email
    assert user.full_name == f"{first_name:s} {last_name:s}"


def test_authentication_getter_new_user_no_email(monkeypatch):
    """
    If no user matches the user's info sub, a user shouldn't be created if it has no email
    """
    klass = OIDCAuthenticationBackend()

    def get_userinfo_mocked(*args):
        return {"sub": "123"}

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert models.User.objects.count() == 0
    assert user is None


def test_authentication_getter_new_user_with_email(monkeypatch):
    """
    If no user matches the user's info sub, a user should be created.
    User's email and name should be set on the identity.
    The "email" field on the User model should not be set as it is reserved for staff users.
    """
    klass = OIDCAuthenticationBackend()

    email = "drive@example.com"

    def get_userinfo_mocked(*args):
        return {"sub": "123", "email": email, "first_name": "John", "last_name": "Doe"}

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert user.sub == "123"
    assert user.email == email
    assert user.full_name == "John Doe"
    assert user.password == "!"
    assert models.User.objects.count() == 1


@override_settings(OIDC_OP_USER_ENDPOINT="http://oidc.endpoint.test/userinfo")
@responses.activate
def test_authentication_get_userinfo_json_response():
    """Test get_userinfo method with a JSON response."""

    responses.add(
        responses.GET,
        re.compile(r".*/userinfo"),
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
        },
        status=200,
    )

    oidc_backend = OIDCAuthenticationBackend()
    result = oidc_backend.get_userinfo("fake_access_token", None, None)

    assert result["first_name"] == "John"
    assert result["last_name"] == "Doe"
    assert result["email"] == "john.doe@example.com"


@override_settings(OIDC_OP_USER_ENDPOINT="http://oidc.endpoint.test/userinfo")
@responses.activate
def test_authentication_get_userinfo_token_response(monkeypatch):
    """Test get_userinfo method with a token response."""

    responses.add(
        responses.GET, re.compile(r".*/userinfo"), body="fake.jwt.token", status=200
    )

    def mock_verify_token(self, token):  # pylint: disable=unused-argument
        return {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@example.com",
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "verify_token", mock_verify_token)

    oidc_backend = OIDCAuthenticationBackend()
    result = oidc_backend.get_userinfo("fake_access_token", None, None)

    assert result["first_name"] == "Jane"
    assert result["last_name"] == "Doe"
    assert result["email"] == "jane.doe@example.com"


@override_settings(OIDC_OP_USER_ENDPOINT="http://oidc.endpoint.test/userinfo")
@responses.activate
def test_authentication_get_userinfo_invalid_response():
    """
    Test get_userinfo method with an invalid JWT response that
    causes verify_token to raise an error.
    """

    responses.add(
        responses.GET, re.compile(r".*/userinfo"), body="fake.jwt.token", status=200
    )

    oidc_backend = OIDCAuthenticationBackend()

    with pytest.raises(
        SuspiciousOperation,
        match="Invalid response format or token verification failed",
    ):
        oidc_backend.get_userinfo("fake_access_token", None, None)


def test_authentication_getter_existing_disabled_user_via_sub(monkeypatch):
    """
    If an existing user matches the sub but is disabled,
    an error should be raised and a user should not be created.
    """

    klass = OIDCAuthenticationBackend()
    db_user = UserFactory(is_active=False)

    def get_userinfo_mocked(*args):
        return {
            "sub": db_user.sub,
            "email": db_user.email,
            "first_name": "John",
            "last_name": "Doe",
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    with (
        pytest.raises(SuspiciousOperation, match="User account is disabled"),
    ):
        klass.get_or_create_user(access_token="test-token", id_token=None, payload=None)

    assert models.User.objects.count() == 1


def test_authentication_getter_existing_disabled_user_via_email(monkeypatch):
    """
    If an existing user does not match the sub but matches the email and is disabled,
    an error should be raised and a user should not be created.
    """

    klass = OIDCAuthenticationBackend()
    db_user = UserFactory(is_active=False)

    def get_userinfo_mocked(*args):
        return {
            "sub": "random",
            "email": db_user.email,
            "first_name": "John",
            "last_name": "Doe",
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    with (
        pytest.raises(SuspiciousOperation, match="User account is disabled"),
    ):
        klass.get_or_create_user(access_token="test-token", id_token=None, payload=None)

    assert models.User.objects.count() == 1


# Essential claims


def test_authentication_verify_claims_default(monkeypatch):
    """The sub claim should be mandatory by default."""
    klass = OIDCAuthenticationBackend()

    def get_userinfo_mocked(*args):
        return {
            "test": "123",
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    with (
        pytest.raises(
            KeyError,
            match="sub",
        ),
    ):
        klass.get_or_create_user(access_token="test-token", id_token=None, payload=None)

    assert models.User.objects.exists() is False


@pytest.mark.parametrize(
    "essential_claims, missing_claims",
    [
        (["email", "sub"], ["email"]),
        (["Email", "sub"], ["Email"]),  # Case sensitivity
    ],
)
@override_settings(OIDC_OP_USER_ENDPOINT="http://oidc.endpoint.test/userinfo")
@mock.patch.object(Logger, "error")
def test_authentication_verify_claims_essential_missing(
    mock_logger,
    essential_claims,
    missing_claims,
    monkeypatch,
):
    """Ensure SuspiciousOperation is raised if essential claims are missing."""

    klass = OIDCAuthenticationBackend()

    def get_userinfo_mocked(*args):
        return {
            "sub": "123",
            "last_name": "Doe",
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    with (
        pytest.raises(
            SuspiciousOperation,
            match="Claims verification failed",
        ),
        override_settings(USER_OIDC_ESSENTIAL_CLAIMS=essential_claims),
    ):
        klass.get_or_create_user(access_token="test-token", id_token=None, payload=None)

    assert models.User.objects.exists() is False
    mock_logger.assert_called_once_with("Missing essential claims: %s", missing_claims)


@override_settings(
    OIDC_OP_USER_ENDPOINT="http://oidc.endpoint.test/userinfo",
    USER_OIDC_ESSENTIAL_CLAIMS=["email", "last_name"],
)
def test_authentication_verify_claims_success(monkeypatch):
    """Ensure user is authenticated when all essential claims are present."""

    klass = OIDCAuthenticationBackend()

    def get_userinfo_mocked(*args):
        return {
            "email": "john.doe@example.com",
            "last_name": "Doe",
            "sub": "123",
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert models.User.objects.filter(id=user.id).exists()

    assert user.sub == "123"
    assert user.full_name == "Doe"
    assert user.email == "john.doe@example.com"


@override_settings(
    OIDC_OP_USER_ENDPOINT="http://oidc.endpoint.test/userinfo",
    USER_OIDC_ESSENTIAL_CLAIMS=["email", "last_name"],
    MESSAGES_TESTDOMAIN="testdomain.bzh",
    MESSAGES_TESTDOMAIN_MAPPING_BASEDOMAIN="gouv.fr",
)
def test_authentication_getter_new_user_with_testdomain(monkeypatch):
    """
    Check the TESTDOMAIN creation process
    """

    klass = OIDCAuthenticationBackend()

    def get_userinfo_mocked(*args):
        return {
            "email": "john.doe@sub.gouv.fr",
            "last_name": "Doe",
            "sub": "123",
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert models.User.objects.filter(id=user.id).exists()

    assert user.sub == "123"
    assert user.full_name == "Doe"
    assert user.email == "john.doe@sub.gouv.fr"

    maildomain = models.MailDomain.objects.get(name="testdomain.bzh")
    mailbox = models.Mailbox.objects.get(local_part="john.doe-sub", domain=maildomain)

    assert models.Contact.objects.filter(
        email="john.doe-sub@testdomain.bzh", mailbox=mailbox
    ).exists()
    assert models.Mailbox.objects.filter(
        local_part="john.doe-sub", domain=maildomain
    ).exists()
    assert models.MailboxAccess.objects.filter(
        mailbox=mailbox,
        user=user,
        role=models.MailboxRoleChoices.ADMIN,
    ).exists()


@override_settings(
    OIDC_OP_USER_ENDPOINT="http://oidc.endpoint.test/userinfo",
    USER_OIDC_ESSENTIAL_CLAIMS=["email", "last_name"],
    MESSAGES_TESTDOMAIN="testdomain.bzh",
    MESSAGES_TESTDOMAIN_MAPPING_BASEDOMAIN="gouv.fr",
)
def test_authentication_getter_new_user_with_testdomain_no_mapping(monkeypatch):
    """
    Check the TESTDOMAIN creation process when email doesn't match
    """

    klass = OIDCAuthenticationBackend()

    def get_userinfo_mocked(*args):
        return {
            "email": "john.doe@notgouv.fr",
            "last_name": "Doe",
            "sub": "123",
        }

    monkeypatch.setattr(OIDCAuthenticationBackend, "get_userinfo", get_userinfo_mocked)

    user = klass.get_or_create_user(
        access_token="test-token", id_token=None, payload=None
    )

    assert user is None

    assert models.User.objects.count() == 0
