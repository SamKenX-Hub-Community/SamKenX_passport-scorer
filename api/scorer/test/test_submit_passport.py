"""Submit address for passport feature tests."""

import json

import pytest
from account.models import Nonce
from django.test import Client
from eth_account.messages import encode_defunct
from pytest_bdd import given, scenario, then, when
from registry.models import Passport
from registry.tasks import score_passport
from registry.test.test_passport_submission import mock_passport
from registry.utils import get_signing_message
from web3 import Web3

web3 = Web3()
web3.eth.account.enable_unaudited_hdwallet_features()

pytestmark = pytest.mark.django_db


@scenario("features/submit_passport.feature", "Submit passport successfully")
def test_submit_passport_successfully():
    """Submit passport successfully."""


@given(
    "that I'm a Passport developer and have a community ID", target_fixture="community"
)
def _(scorer_community_with_gitcoin_default):
    """that I'm a Passport developer and have a community ID."""
    pass


@when(
    "I call the submit-passport API for an Ethereum account under that community ID",
    target_fixture="score_response",
)
def _(scorer_api_key, scorer_community_with_gitcoin_default, mocker):
    """I call the submit-passport API for an Ethereum account under that community ID."""

    mocker.patch("registry.tasks.get_passport", return_value=mock_passport)
    mocker.patch("registry.tasks.validate_credential", side_effect=[[], []])
    client = Client()

    my_mnemonic = (
        "chief loud snack trend chief net field husband vote message decide replace"
    )
    web3_account = web3.eth.account.from_mnemonic(
        my_mnemonic, account_path="m/44'/60'/0'/0/0"
    )

    nonce = Nonce.create_nonce().nonce
    signing_message = get_signing_message(nonce)

    signed_message = web3.eth.account.sign_message(
        encode_defunct(text=signing_message),
        private_key=web3_account.key,
    )

    payload = {
        "community": scorer_community_with_gitcoin_default.id,
        "address": scorer_community_with_gitcoin_default.account.address,
        "signature": signed_message.signature.hex(),
        "nonce": nonce,
    }

    submit_response = client.post(
        "/registry/submit-passport",
        json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Token {scorer_api_key}",
    )

    # execute the task
    score_passport(
        scorer_community_with_gitcoin_default.id,
        scorer_community_with_gitcoin_default.account.address,
    )

    # read the score ...
    assert submit_response.json() == {
        "address": scorer_community_with_gitcoin_default.account.address.lower(),
        "score": None,
        "status": "PROCESSING",
        "last_score_timestamp": None,
        "evidence": None,
        "error": None,
    }
    response = client.get(
        f"/registry/score/{scorer_community_with_gitcoin_default.id}/{scorer_community_with_gitcoin_default.account.address}",
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {scorer_api_key}",
    )

    return response


@then(
    "the API logs all of the valid Passport data points (VCs), namely the complete JSON, mapped to that Passport holder within the respective community ID directory"
)
def _(scorer_community_with_gitcoin_default, score_response):
    """the API logs all of the valid Passport data points (VCs), namely the complete JSON, mapped to that Passport holder within the respective community ID directory."""
    assert score_response.status_code == 200

    assert len(Passport.objects.all()) == 1
    passport = Passport.objects.all()[0]

    assert passport.community.id == scorer_community_with_gitcoin_default.id


@then("the API reads all of the Passport data points")
def _():
    """the API reads all of the Passport data points."""
    pass


@scenario(
    "features/submit_passport.feature",
    "As a developer, I want to rely on the Gitcoin Community Scorer scoring settings of the API",
)
def test_as_a_developer_i_want_to_rely_on_the_gitcoin_community_scorer_scoring_settings_of_the_api():
    """As a developer, I want to rely on the Gitcoin Community Scorer scoring settings of the API."""
    pass


@given("I have not further configured its settings")
def _():
    """I have not further configured its settings."""
    # Nothingg to do here
    pass


@given("that I have created a community ID")
def _(scorer_community_with_gitcoin_default):
    """that I have created a community ID."""
    pass


@then(
    "I want to get a score based on the Gitcoin Community Score and deduplication rules (see default deduplication settings here)"
)
def _(score_response):
    """I want to get a score based on the Gitcoin Community Score and deduplication rules (see default deduplication settings here)."""

    assert score_response.status_code == 200
    score_response_data = score_response.json()
    assert (
        score_response_data["address"] == "0xb81c935d01e734b3d8bb233f5c4e1d72dbc30f6c"
    )
    assert score_response_data["score"] == "1001234.000000000"
    assert score_response_data["evidence"] == None
    assert score_response_data["status"] == "DONE"
    # assert score_response_data["last_score_timestamp"] == None    # TODO check that timestamp is recent


@then(
    "log the score associated with this Passport under the corresponding community ID"
)
def _(scorer_community_with_gitcoin_default, scorer_api_key):
    """log the score associated with this Passport under the corresponding community ID."""
    client = Client()

    score_response = client.get(
        f"/registry/score/{scorer_community_with_gitcoin_default.id}/{scorer_community_with_gitcoin_default.account.address}",
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Token {scorer_api_key}",
    )

    # TODO: This checks essentially the same thing as previous step. Logic of the test scnario might need a rework
    score_response_data = score_response.json()
    assert (
        score_response_data["address"] == "0xb81c935d01e734b3d8bb233f5c4e1d72dbc30f6c"
    )
    assert score_response_data["score"] == "1001234.000000000"
    assert score_response_data["evidence"] == None
    assert score_response_data["status"] == "DONE"
    # assert score_response_data["last_score_timestamp"] == None    # TODO check that timestamp is recent
