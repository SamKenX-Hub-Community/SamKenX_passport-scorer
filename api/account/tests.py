from django.test import TestCase
from django.test import Client

# Create your tests here.
from .models import Account

from web3.auto import w3
from web3 import Web3
from eth_account.messages import encode_defunct
import binascii
import json
from datetime import datetime
from siwe import SiweMessage
from copy import deepcopy


class AccountTestCase(TestCase):
    def setUp(self):
        pass

    def test_create_account_with_SIWE(self):
        """Test creation of an account wit SIWE"""
        web3 = Web3()
        web3.eth.account.enable_unaudited_hdwallet_features()
        # TODO: load mnemonic from env
        my_mnemonic = (
            "chief loud snack trend chief net field husband vote message decide replace"
        )
        account = web3.eth.account.from_mnemonic(
            my_mnemonic, account_path="m/44'/60'/0'/0/0"
        )
        print("account", account.address)

        c = Client()
        response = c.get("/account/challenge?address={account.address}")
        self.assertEqual(200, response.status_code)

        data = response.json()
        # TODO: verify data
        print("Data", data)

        siwe_data = {
            "domain": "localhost",
            "address": account.address,
            "statement": "Sign in with Ethereum to the app.",
            "uri": "http://localhost/",
            "version": "1",
            "chainId": "1",
            "nonce": data["nonce"],
            "issuedAt": datetime.utcnow().isoformat(),
        }

        siwe_data_pay = deepcopy(siwe_data)
        siwe_data_pay["chain_id"] = siwe_data_pay["chainId"]
        siwe_data_pay["issued_at"] = siwe_data_pay["issuedAt"]

        siwe = SiweMessage(siwe_data_pay)
        data_to_sign = siwe.prepare_message()

        private_key = account.key
        signed_message = w3.eth.account.sign_message(
            encode_defunct(text=data_to_sign), private_key=private_key
        )

        response = c.post(
            "/account/verify",
            json.dumps(
                {
                    "message": siwe_data,
                    "signature": binascii.hexlify(signed_message.signature).decode(
                        "utf-8"
                    ),
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)
        data = response.json()
        # TODO: check payload of the JWT token ???
        self.assertTrue("refresh" in data)
        self.assertTrue("access" in data)