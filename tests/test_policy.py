from pathlib import Path

import pytest

from core.policy import NetworkPolicy, PolicyViolation


@pytest.fixture
def policy():
    return NetworkPolicy.load(Path(__file__).parents[1] / "policies" / "network_policy.yaml")


def test_accepts_lab_address(policy):
    assert policy.validate_ip("10.2.3.4") == "10.2.3.4"


@pytest.mark.parametrize("value", ["192.168.1.1", "8.8.8.8", "not-an-ip", "::1"])
def test_rejects_disallowed_or_invalid_ip(policy, value):
    with pytest.raises(PolicyViolation):
        policy.validate_ip(value)


@pytest.mark.parametrize("value", [0, 101])
def test_rejects_bandwidth_outside_policy(policy, value):
    with pytest.raises(PolicyViolation):
        policy.validate_limit(value)
