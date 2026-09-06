from app import access
from app.main import DevLoginCreate, dev_login


def test_public_dev_login_cannot_create_privileged_roles_from_arbitrary_input():
    result = dev_login(DevLoginCreate(user="demo-student"))
    assert result["user"]["roles"] == ["student"]
    assert "admin.products.manage" not in result["permissions"]


def test_guardian_purchase_uses_backend_price_and_selected_beneficiary():
    order = access.create_order("demo-guardian", "iaq-complete", "demo-student")
    assert order["beneficiary_user_id"] == "demo-student"
    assert order["currency"] == "IDR"
    assert order["total_minor"] == 14900000
    assert "amount" not in order


def test_mock_settlement_is_idempotent_and_creates_one_entitlement():
    order = access.create_order("demo-guardian", "iaq-complete", "demo-student")
    access.create_payment_attempt(order["id"])
    first = access.settle_mock_payment(order["id"], "demo-guardian")
    second = access.settle_mock_payment(order["id"], "demo-guardian")
    assert first["status"] == second["status"] == "fulfilled"
    matching = [item for item in access.ENTITLEMENTS.values() if item["source_id"] == order["id"]]
    assert len(matching) == 2  # start access + complete report


def test_school_seat_cannot_be_allocated_twice_to_same_student():
    try:
        access.allocate_school_seat("school-demo", "demo-student", "demo-school-admin")
    except ValueError as error:
        assert "already has" in str(error)
    else:
        raise AssertionError("duplicate seat allocation should be rejected")
