#!/usr/bin/python

import os
import pyln
import pytest
from pyln.testing import utils
from pyln.testing.fixtures import *  # noqa: F403
from util import LightningD

pyln.testing.fixtures.network_daemons["signet"] = utils.BitcoinD

class LightningNode(utils.LightningNode):
    def __init__(self, *args, **kwargs):
        pyln.testing.utils.TEST_NETWORK = "signet"
        utils.LightningNode.__init__(self, *args, **kwargs)
        lightning_dir = args[1]
        old_opts = self.daemon.opts
        self.daemon = LightningD(lightning_dir, None)  # noqa: F405
        new_opts = {
            "disable-plugin": ["bcli"],
            "network": "signet",
            "plugin": os.path.join(os.path.dirname(__file__), "../sauron.py"),
            "sauron-api-endpoint": "https://mutinynet.com/api",
        }
        self.daemon.opts.update(old_opts)
        self.daemon.opts.update(new_opts)
        opts_to_disable = [
            "bitcoin-datadir",
            "bitcoin-rpcpassword",
            "bitcoin-rpcuser",
            "dev-bitcoind-poll",
        ]
        for opt in opts_to_disable:
            self.daemon.opts.pop(opt)

    # Monkey patch
    def set_feerates(self, feerates, wait_for_effect=True):
        return None

@pytest.fixture
def node_cls(monkeypatch):
    monkeypatch.setenv("TEST_NETWORK", "signet")
    yield LightningNode


def test_mempoolspace_signet_getchaininfo(node_factory):
    """
    Test getchaininfo
    """
    ln_node = node_factory.get_node()

    response = ln_node.rpc.call("getchaininfo")

    assert ln_node.daemon.is_in_log("Sauron plugin initialized using mempool.space API")

    expected_response_keys = ["chain", "blockcount", "headercount", "ibd"]
    assert list(response.keys()) == expected_response_keys
    assert response["chain"] == "signet"
    assert not response["ibd"]


def test_mempoolspace_signet_getrawblockbyheight(node_factory):
    """
    Test getrawblockbyheight
    """
    ln_node = node_factory.get_node()

    response = ln_node.rpc.call("getrawblockbyheight", {"height": 0})

    expected_response = {
        "block": "0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a008f4d5fae77031e8ad222030101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4d04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73ffffffff0100f2052a01000000434104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac00000000",
        "blockhash": "00000008819873e925422c1ff0f99f7cc9bbb232af63a077a480a3633bee1ef6",
    }
    assert response == expected_response

@pytest.mark.skip(reason="testing_theory")
def test_mempoolspace_signet_sendrawtransaction_invalid(node_factory):
    """
    Test sendrawtransaction
    """
    ln_node = node_factory.get_node()

    expected_response = {
        "errmsg": 'sendrawtransaction RPC error: {"code":-22,"message":"TX decode failed. Make sure the tx has at least one input."}',
        "success": False,
    }
    response = ln_node.rpc.call(
        "sendrawtransaction",
        {"tx": "invalid-raw-tx"},
    )

    assert response == expected_response


def test_mempoolspace_signet_getutxout(node_factory):
    """
    Test getutxout
    """
    ln_node = node_factory.get_node()

    expected_response = {
        "amount": 5000000000,
        "script": "4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac",
    }
    response = ln_node.rpc.call(
        "getutxout",
        {
            # coinbase tx block 0
            "txid": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
            "vout": 0,
        },
    )
    assert response == expected_response


def test_mempoolspace_signet_estimatefees(node_factory):
    """
    Test estimatefees
    """
    ln_node = node_factory.get_node()

    # Sample response
    # {
    #     "opening": 1000,
    #     "mutual_close": 1000,
    #     "unilateral_close": 1000,
    #     "delayed_to_us": 1000,
    #     "htlc_resolution": 1000,
    #     "penalty": 1000,
    #     "min_acceptable": 500,
    #     "max_acceptable": 10000,
    #     "feerate_floor": 1000000,
    #     "feerates": [
    #         {"blocks": 2, "feerate": 1000},
    #         {"blocks": 6, "feerate": 1000},
    #         {"blocks": 12, "feerate": 1000},
    #         {"blocks": 144, "feerate": 1000}
    #     ]
    # }

    response = ln_node.rpc.call("estimatefees")

    expected_response_keys = [
        "opening",
        "mutual_close",
        "unilateral_close",
        "delayed_to_us",
        "htlc_resolution",
        "penalty",
        "min_acceptable",
        "max_acceptable",
        "feerate_floor",
        "feerates",
    ]
    assert list(response.keys()) == expected_response_keys

    expected_feerates_keys = ("blocks", "feerate")
    assert (
        list(set([tuple(entry.keys()) for entry in response["feerates"]]))[0]
        == expected_feerates_keys
    )

    expected_feerates_blocks = [2, 6, 12, 144]
    assert [
        entry["blocks"] for entry in response["feerates"]
    ] == expected_feerates_blocks
