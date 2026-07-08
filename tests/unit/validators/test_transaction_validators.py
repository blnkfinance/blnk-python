"""Unit tests for the transaction validators.

74 cases in 10 groups — one test class per group, one test function per
case (short case name in the docstring). All cases are direct validator
calls (no mocks, no HTTP).
"""

from datetime import datetime, timezone

from blnk_sdk.constants import MAX_BULK_CREATE_ITEMS, MAX_BULK_INFLIGHT_ITEMS
from blnk_sdk.validators.transaction_validators import (
    validate_bulk_commit_inflight,
    validate_bulk_transactions,
    validate_bulk_void_inflight,
    validate_create_transactions,
    validate_recover_queue,
    validate_refund_transaction,
    validate_update_transactions,
)

BASE_FIELDS = {
    "precision": 100,
    "reference": "ref_split_001",
    "description": "Split transaction",
    "currency": "USD",
}


class TestAtomicOnSplitTransactions:
    """atomic on split transactions"""

    def test_allows_atomic_on_split_create_payloads(self):
        """allows atomic on split create payloads"""
        data = {
            "amount": 1000,
            "precision": 100,
            "reference": "ref_atomic_split",
            "description": "Atomic split",
            "currency": "USD",
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": "50%"},
                {"identifier": "bln_recipient", "distribution": "left"},
            ],
            "atomic": True,
        }

        assert validate_create_transactions(data) is None

    def test_rejects_non_boolean_atomic(self):
        """rejects non-boolean atomic"""
        data = {
            "amount": 1000,
            "precision": 100,
            "reference": "ref_bad_atomic",
            "description": "Bad atomic",
            "currency": "USD",
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": "50%"},
                {"identifier": "bln_recipient", "distribution": "left"},
            ],
            "atomic": "true",
        }

        assert (
            validate_create_transactions(data)
            == "atomic must be a boolean if provided."
        )


class TestSplitTransactionValidator:
    """split-transaction validator"""

    def test_allows_multiple_sources_with_a_single_destination(self):
        """allows multiple sources with a single destination"""
        data = {
            **BASE_FIELDS,
            "amount": 30000,
            "sources": [
                {"identifier": "bln_alice", "distribution": "10%"},
                {"identifier": "bln_bob", "distribution": "20000"},
                {"identifier": "bln_charlie", "distribution": "left"},
            ],
            "destination": "bln_sarah",
        }

        assert validate_create_transactions(data) is None

    def test_allows_a_single_source_with_multiple_destinations(self):
        """allows a single source with multiple destinations"""
        data = {
            **BASE_FIELDS,
            "amount": 30000,
            "source": "bln_sarah",
            "destinations": [
                {"identifier": "bln_alice", "distribution": "10%"},
                {"identifier": "bln_bob", "distribution": "20000"},
                {"identifier": "bln_charlie", "distribution": "left"},
            ],
        }

        assert validate_create_transactions(data) is None

    def test_rejects_sources_without_destination(self):
        """rejects sources without destination"""
        data = {
            **BASE_FIELDS,
            "amount": 30000,
            "sources": [{"identifier": "bln_alice", "distribution": "100%"}],
        }

        assert (
            validate_create_transactions(data)
            == "'destination' is required when using 'sources'."
        )

    def test_rejects_destinations_without_source(self):
        """rejects destinations without source"""
        data = {
            **BASE_FIELDS,
            "amount": 30000,
            "destinations": [{"identifier": "bln_alice", "distribution": "100%"}],
        }

        assert (
            validate_create_transactions(data)
            == "'source' is required when using 'destinations'."
        )

    def test_rejects_sources_with_destinations_array(self):
        """rejects sources with destinations array"""
        data = {
            **BASE_FIELDS,
            "amount": 30000,
            "sources": [{"identifier": "bln_alice", "distribution": "100%"}],
            "destination": "bln_sarah",
            "destinations": [{"identifier": "bln_bob", "distribution": "left"}],
        }

        assert (
            validate_create_transactions(data)
            == "Both 'destination' and 'destinations' cannot be provided together."
        )

    def test_rejects_sources_combined_with_destinations_routing(self):
        """rejects sources combined with destinations routing"""
        data = {
            **BASE_FIELDS,
            "amount": 30000,
            "sources": [{"identifier": "bln_alice", "distribution": "100%"}],
            "destinations": [{"identifier": "bln_bob", "distribution": "100%"}],
        }

        assert validate_create_transactions(data) == (
            "'sources' requires a single 'destination'; "
            "use 'destination' instead of 'destinations'."
        )

    def test_uses_correct_error_message_when_destination_and_destinations_are_both_set(
        self,
    ):
        """uses correct error message when destination and destinations are both set"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "bln_source",
            "destination": "bln_dest_a",
            "destinations": [{"identifier": "bln_dest_b", "distribution": "100%"}],
        }

        assert (
            validate_create_transactions(data)
            == "Both 'destination' and 'destinations' cannot be provided together."
        )
        # must not reuse the source/sources error message
        assert (
            validate_create_transactions(data)
            != "Both 'source' and 'sources' cannot be provided together."
        )

    def test_allows_precise_amount_only_payloads(self):
        """allows precise_amount-only payloads"""
        data = {
            **BASE_FIELDS,
            "precise_amount": 3000000,
            "source": "@FundingPool",
            "destination": "bln_recipient",
        }

        assert validate_create_transactions(data) is None

    def test_allows_precise_amount_only_with_multiple_sources_split(self):
        """allows precise_amount-only with multiple sources split"""
        data = {
            **BASE_FIELDS,
            "precise_amount": 3000000,
            "sources": [
                {"identifier": "bln_alice", "distribution": "10%"},
                {"identifier": "bln_bob", "distribution": "2000000"},
                {"identifier": "bln_charlie", "distribution": "left"},
            ],
            "destination": "bln_sarah",
        }

        assert validate_create_transactions(data) is None

    def test_rejects_when_neither_amount_nor_precise_amount_is_provided(self):
        """rejects when neither amount nor precise_amount is provided"""
        data = {
            **BASE_FIELDS,
            "source": "bln_a",
            "destination": "bln_b",
        }

        assert (
            validate_create_transactions(data)
            == "Either 'amount' or 'precise_amount' must be provided."
        )

    def test_allows_split_legs_that_use_precise_distribution_only(self):
        """allows split legs that use precise_distribution only"""
        data = {
            **BASE_FIELDS,
            "precise_amount": 10000,
            "source": "bln_sarah",
            "destinations": [
                {"identifier": "bln_merchant", "precise_distribution": "9733"},
                {"identifier": "bln_fee", "precise_distribution": "267"},
            ],
        }

        assert validate_create_transactions(data) is None

    def test_allows_mixed_precise_distribution_and_percentage_distribution_legs(self):
        """allows mixed precise_distribution and percentage distribution legs"""
        data = {
            **BASE_FIELDS,
            "precise_amount": "189207535698279000",
            "source": "bln_sarah",
            "destinations": [
                {
                    "identifier": "bln_alice",
                    "precise_distribution": "37841507139655800",
                },
                {"identifier": "bln_bob", "distribution": "20%"},
                {"identifier": "bln_charlie", "distribution": "left"},
            ],
        }

        assert validate_create_transactions(data) is None

    def test_validates_precise_distribution_strings_beyond_number_max_safe_integer_exactly(
        self,
    ):
        """validates precise_distribution strings beyond Number.MAX_SAFE_INTEGER exactly"""
        leg_a = "9007199254740992"
        leg_b = "1"
        total = "9007199254740993"

        valid = {
            **BASE_FIELDS,
            "precise_amount": total,
            "source": "bln_sarah",
            "destinations": [
                {"identifier": "bln_alice", "precise_distribution": leg_a},
                {"identifier": "bln_bob", "precise_distribution": leg_b},
            ],
        }

        invalid = {
            **valid,
            "destinations": [
                {"identifier": "bln_alice", "precise_distribution": leg_a},
                {"identifier": "bln_bob", "precise_distribution": "2"},
            ],
        }

        assert validate_create_transactions(valid) is None
        # Legs must sum exactly: the values are compared as arbitrary-precision
        # integers, so float parsing (which rounds 9007199254740993) never applies.
        assert validate_create_transactions(invalid) is not None

    def test_allows_precise_amount_as_a_string_for_large_integers(self):
        """allows precise_amount as a string for large integers"""
        data = {
            **BASE_FIELDS,
            "precise_amount": "9007199254740993",
            "source": "@FundingPool",
            "destination": "bln_recipient",
        }

        assert validate_create_transactions(data) is None

    def test_rejects_invalid_precise_amount_string_values(self):
        """rejects invalid precise_amount string values"""
        data = {
            **BASE_FIELDS,
            "precise_amount": "12.5",
            "source": "bln_a",
            "destination": "bln_b",
        }

        assert (
            validate_create_transactions(data)
            == "precise_amount must be a non-negative integer string or number."
        )

    def test_rejects_split_legs_missing_both_distribution_and_precise_distribution(
        self,
    ):
        """rejects split legs missing both distribution and precise_distribution"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "bln_sarah",
            "destinations": [{"identifier": "bln_alice"}],
        }

        assert validate_create_transactions(data) == (
            "Each destination leg must include either "
            "'distribution' or 'precise_distribution'."
        )

    def test_rejects_invalid_precise_distribution_values(self):
        """rejects invalid precise_distribution values"""
        data = {
            **BASE_FIELDS,
            "precise_amount": 1000,
            "source": "bln_sarah",
            "destinations": [
                {"identifier": "bln_alice", "precise_distribution": "not-a-number"},
            ],
        }

        assert (
            validate_create_transactions(data)
            == "Invalid precise_distribution for leg: bln_alice."
        )

    def test_uses_amount_for_distribution_math_when_both_amount_and_precise_amount_are_provided(
        self,
    ):
        """uses amount for distribution math when both amount and precise_amount are provided"""
        valid_with_amount = {
            **BASE_FIELDS,
            "amount": 10000,
            "precise_amount": 999999,
            "source": "bln_sarah",
            "destinations": [
                {"identifier": "bln_merchant", "precise_distribution": "9733"},
                {"identifier": "bln_fee", "precise_distribution": "267"},
            ],
        }

        invalid_if_precise_amount_used = {
            **BASE_FIELDS,
            "amount": 10000,
            "precise_amount": 999999,
            "source": "bln_sarah",
            "destinations": [
                {"identifier": "bln_merchant", "precise_distribution": "999998"},
                {"identifier": "bln_fee", "precise_distribution": "1"},
            ],
        }

        assert validate_create_transactions(valid_with_amount) is None
        # amount (10000) should take precedence over precise_amount (999999)
        assert validate_create_transactions(invalid_if_precise_amount_used) is not None


class TestCreateTransactionRequestFields:
    """create transaction request fields"""

    def test_allows_skip_queue_on_create_payloads(self):
        """allows skip_queue on create payloads"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "skip_queue": True,
        }

        assert validate_create_transactions(data) is None

    def test_allows_effective_date_as_an_iso_string(self):
        """allows effective_date as an ISO string"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "effective_date": "2025-02-15T10:30:00Z",
        }

        assert validate_create_transactions(data) is None

    def test_allows_inflight_commit_date_as_core_example_string(self):
        """allows inflight_commit_date as Core example string"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "inflight": True,
            "inflight_commit_date": "2024-04-22T15:28:03+00:00",
        }

        assert validate_create_transactions(data) is None

    def test_allows_inflight_commit_date_as_a_date(self):
        """allows inflight_commit_date as a datetime"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "inflight": True,
            "inflight_commit_date": datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        }

        assert validate_create_transactions(data) is None

    def test_allows_effective_date_with_a_numeric_timezone_offset(self):
        """allows effective_date with a numeric timezone offset"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "effective_date": "2024-04-22T15:28:03+00:00",
        }

        assert validate_create_transactions(data) is None

    def test_rejects_date_only_effective_date_strings(self):
        """rejects date-only effective_date strings"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "effective_date": "2025-02-15",
        }

        assert validate_create_transactions(data) == "Invalid effective_date."

    def test_rejects_invalid_skip_queue_values(self):
        """rejects invalid skip_queue values"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "skip_queue": "true",
        }

        assert (
            validate_create_transactions(data)
            == "skip_queue must be a boolean if provided."
        )

    def test_rejects_invalid_effective_date_values(self):
        """rejects invalid effective_date values"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "effective_date": "not-a-date",
        }

        assert validate_create_transactions(data) == "Invalid effective_date."

    def test_rejects_invalid_inflight_commit_date_values(self):
        """rejects invalid inflight_commit_date values"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "inflight_commit_date": "bad-date",
        }

        assert validate_create_transactions(data) == "Invalid inflight_commit_date."

    def test_allows_scheduled_for_as_an_iso_string(self):
        """allows scheduled_for as an ISO string"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "scheduled_for": "2025-12-31T23:59:59Z",
        }

        assert validate_create_transactions(data) is None

    def test_rejects_date_only_scheduled_for_strings(self):
        """rejects date-only scheduled_for strings"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "scheduled_for": "2025-12-31",
        }

        assert validate_create_transactions(data) == "Invalid scheduled date."


class TestIsoDateStringsAndDistribution:
    """ISO date strings and Distribution handling"""

    def test_allows_scheduled_for_as_an_iso_string_on_create(self):
        """allows scheduled_for as an ISO string on create"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "scheduled_for": "2025-07-01T08:00:00Z",
        }

        assert validate_create_transactions(data) is None

    def test_allows_inflight_expiry_date_as_an_iso_string_on_create(self):
        """allows inflight_expiry_date as an ISO string on create"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destination": "@Recipient",
            "inflight": True,
            "inflight_expiry_date": "2025-08-01T08:00:00Z",
        }

        assert validate_create_transactions(data) is None

    def test_allows_decimal_fixed_distribution_strings_such_as_240_23(self):
        """allows decimal fixed distribution strings such as 240.23"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": "240.23"},
                {"identifier": "bln_recipient", "distribution": "left"},
            ],
        }

        assert validate_create_transactions(data) is None

    def test_allows_decimal_distribution_when_precise_distribution_is_on_another_leg(
        self,
    ):
        """allows decimal distribution when precise_distribution is on another leg"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": "240.23"},
                {"identifier": "bln_recipient", "precise_distribution": "500"},
                {"identifier": "bln_treasury", "distribution": "left"},
            ],
        }

        assert validate_create_transactions(data) is None

    def test_allows_exact_decimal_sum_without_left(self):
        """allows exact decimal sum without left"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": "240.23"},
                {"identifier": "bln_recipient", "distribution": "759.77"},
            ],
        }

        assert validate_create_transactions(data) is None

    def test_rejects_scientific_notation_distribution_strings(self):
        """rejects scientific notation distribution strings"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": "1e3"},
                {"identifier": "bln_recipient", "distribution": "left"},
            ],
        }

        assert (
            validate_create_transactions(data)
            == "Invalid distribution type for leg: bln_fee."
        )

    def test_rejects_hex_distribution_strings(self):
        """rejects hex distribution strings"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": "0x10"},
                {"identifier": "bln_recipient", "distribution": "left"},
            ],
        }

        assert (
            validate_create_transactions(data)
            == "Invalid distribution type for leg: bln_fee."
        )

    def test_rejects_whitespace_padded_distribution_strings(self):
        """rejects whitespace-padded distribution strings"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": " 240.23 "},
                {"identifier": "bln_recipient", "distribution": "left"},
            ],
        }

        assert (
            validate_create_transactions(data)
            == "Invalid distribution type for leg: bln_fee."
        )

    def test_rejects_infinity_distribution_strings(self):
        """rejects Infinity distribution strings"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": "Infinity"},
                {"identifier": "bln_recipient", "distribution": "left"},
            ],
        }

        assert (
            validate_create_transactions(data)
            == "Invalid distribution type for leg: bln_fee."
        )

    def test_rejects_malformed_decimal_distribution_strings(self):
        """rejects malformed decimal distribution strings"""
        data = {
            **BASE_FIELDS,
            "amount": 1000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_fee", "distribution": "240.23.1"},
                {"identifier": "bln_recipient", "distribution": "left"},
            ],
        }

        assert (
            validate_create_transactions(data)
            == "Invalid distribution type for leg: bln_fee."
        )

    def test_allows_decimal_percentage_distributions_with_precise_amount(self):
        """allows decimal percentage distributions with precise_amount"""
        data = {
            **BASE_FIELDS,
            "precise_amount": 30000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_a", "distribution": "33.33%"},
                {"identifier": "bln_b", "distribution": "66.67%"},
            ],
        }

        assert validate_create_transactions(data) is None

    def test_allows_decimal_percentage_with_left_under_precise_distribution_split(
        self,
    ):
        """allows decimal percentage with left under precise_distribution split"""
        data = {
            **BASE_FIELDS,
            "amount": 30000,
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_a", "distribution": "33.33%"},
                {"identifier": "bln_b", "precise_distribution": "5000"},
                {"identifier": "bln_c", "distribution": "left"},
            ],
        }

        assert validate_create_transactions(data) is None

    def test_rejects_decimal_distributions_with_precise_amount_beyond_max_safe_integer(
        self,
    ):
        """rejects decimal distributions with precise_amount beyond MAX_SAFE_INTEGER"""
        data = {
            **BASE_FIELDS,
            "precise_amount": "9007199254740993",
            "source": "@FundingPool",
            "destinations": [
                {"identifier": "bln_a", "distribution": "33.33%"},
                {"identifier": "bln_b", "distribution": "left"},
            ],
        }

        assert validate_create_transactions(data) == (
            "Decimal distribution values are not supported with "
            "precise amounts beyond Number.MAX_SAFE_INTEGER."
        )


BASE_BULK_TXN = {
    **BASE_FIELDS,
    "amount": 1000,
    "source": "@FundingPool",
    "destination": "@Recipient",
}


class TestBulkTransactionRequestFields:
    """bulk transaction request fields"""

    def test_allows_skip_queue_on_bulk_payloads(self):
        """allows skip_queue on bulk payloads"""
        data = {
            "skip_queue": True,
            "transactions": [
                {**BASE_BULK_TXN, "reference": "bulk_ref_001"},
                {**BASE_BULK_TXN, "reference": "bulk_ref_002", "amount": 2000},
            ],
        }

        assert validate_bulk_transactions(data) is None

    def test_rejects_invalid_skip_queue_on_bulk_payloads(self):
        """rejects invalid skip_queue on bulk payloads"""
        data = {
            "skip_queue": "true",
            "transactions": [
                {**BASE_BULK_TXN, "reference": "bulk_ref_001"},
                {**BASE_BULK_TXN, "reference": "bulk_ref_002", "amount": 2000},
            ],
        }

        assert (
            validate_bulk_transactions(data)
            == "skip_queue must be a boolean if provided."
        )

    def test_rejects_oversized_transactions_array(self):
        """rejects oversized transactions array"""
        transactions = [
            {**BASE_BULK_TXN, "reference": f"bulk_ref_{i}"}
            for i in range(MAX_BULK_CREATE_ITEMS + 1)
        ]

        assert (
            validate_bulk_transactions({"transactions": transactions})
            == f"Too many transactions; max is {MAX_BULK_CREATE_ITEMS}."
        )


class TestUpdateStatusPreciseAmountOnPartialCommit:
    """updateStatus precise_amount on partial commit"""

    def test_allows_commit_with_precise_amount_only(self):
        """allows commit with precise_amount only"""
        data = {
            "status": "commit",
            "precise_amount": 50000,
        }

        assert validate_update_transactions(data) is None

    def test_allows_precise_amount_as_a_string_for_large_integers(self):
        """allows precise_amount as a string for large integers"""
        data = {
            "status": "commit",
            "precise_amount": "9007199254740993",
        }

        assert validate_update_transactions(data) is None

    def test_allows_full_commit_without_amount_or_precise_amount(self):
        """allows full commit without amount or precise_amount"""
        data = {
            "status": "commit",
        }

        assert validate_update_transactions(data) is None

    def test_allows_amount_and_precise_amount_together(self):
        """allows amount and precise_amount together"""
        data = {
            "status": "commit",
            "amount": 500,
            "precise_amount": 50000,
        }

        assert validate_update_transactions(data) is None

    def test_rejects_invalid_precise_amount_string_values(self):
        """rejects invalid precise_amount string values"""
        data = {
            "status": "commit",
            "precise_amount": "12.5",
        }

        assert (
            validate_update_transactions(data)
            == "precise_amount must be a non-negative integer string or number."
        )

    def test_rejects_unknown_fields(self):
        """rejects unknown fields"""
        data = {
            "status": "commit",
            "precise_amount": 50000,
            "currency": "USD",
        }

        assert validate_update_transactions(data) == "Invalid field: currency"

    def test_allows_skip_queue_on_update_payloads(self):
        """allows skip_queue on update payloads"""
        data = {
            "status": "commit",
            "skip_queue": True,
        }

        assert validate_update_transactions(data) is None

    def test_rejects_invalid_skip_queue_on_update_payloads(self):
        """rejects invalid skip_queue on update payloads"""
        data = {
            "status": "commit",
            "skip_queue": "true",
        }

        assert (
            validate_update_transactions(data)
            == "skip_queue must be a boolean if provided."
        )


class TestRefundTransactionRequestFields:
    """refund transaction request fields"""

    def test_allows_skip_queue_on_refund_payloads(self):
        """allows skip_queue on refund payloads"""
        data = {"skip_queue": True}
        assert validate_refund_transaction(data) is None

    def test_allows_empty_refund_options_object(self):
        """allows empty refund options object"""
        data = {}
        assert validate_refund_transaction(data) is None

    def test_rejects_invalid_skip_queue_on_refund_payloads(self):
        """rejects invalid skip_queue on refund payloads"""
        data = {"skip_queue": "true"}
        assert (
            validate_refund_transaction(data)
            == "skip_queue must be a boolean if provided."
        )

    def test_rejects_unknown_fields_on_refund_payloads(self):
        """rejects unknown fields on refund payloads"""
        data = {
            "skip_queue": True,
            "amount": 100,
        }

        assert validate_refund_transaction(data) == "Invalid field: amount"


class TestBulkCommitInflightValidation:
    """bulkCommitInflight validation"""

    def test_allows_valid_bulk_commit_inflight_payloads(self):
        """allows valid bulk commit inflight payloads"""
        data = {
            "transactions": [
                {"transaction_id": "txn_11111111-1111-4111-8111-111111111111"},
                {
                    "transaction_id": "txn_22222222-2222-4222-8222-222222222222",
                    "amount": 40,
                    "precise_amount": "125034",
                },
            ],
        }

        assert validate_bulk_commit_inflight(data) is None

    def test_rejects_empty_transactions_array(self):
        """rejects empty transactions array"""
        assert (
            validate_bulk_commit_inflight({"transactions": []})
            == "Transactions array cannot be empty."
        )

    def test_rejects_oversized_transactions_array(self):
        """rejects oversized transactions array"""
        transactions = [
            {"transaction_id": "txn_test"}
            for _ in range(MAX_BULK_INFLIGHT_ITEMS + 1)
        ]

        assert (
            validate_bulk_commit_inflight({"transactions": transactions})
            == f"Too many transactions; max is {MAX_BULK_INFLIGHT_ITEMS}."
        )

    def test_rejects_invalid_precise_amount(self):
        """rejects invalid precise_amount"""
        data = {
            "transactions": [
                {
                    "transaction_id": "txn_11111111-1111-4111-8111-111111111111",
                    "precise_amount": "-1",
                },
            ],
        }

        assert validate_bulk_commit_inflight(data) == (
            "precise_amount must be a non-negative integer string "
            "or number at index 0."
        )

    def test_allows_skip_queue_on_bulk_commit_payloads(self):
        """allows skip_queue on bulk commit payloads"""
        data = {
            "skip_queue": True,
            "transactions": [
                {"transaction_id": "txn_11111111-1111-4111-8111-111111111111"}
            ],
        }

        assert validate_bulk_commit_inflight(data) is None

    def test_rejects_invalid_skip_queue_on_bulk_commit_payloads(self):
        """rejects invalid skip_queue on bulk commit payloads"""
        data = {
            "skip_queue": "true",
            "transactions": [
                {"transaction_id": "txn_11111111-1111-4111-8111-111111111111"}
            ],
        }

        assert (
            validate_bulk_commit_inflight(data)
            == "skip_queue must be a boolean if provided."
        )


class TestBulkVoidInflightValidation:
    """bulkVoidInflight validation"""

    def test_allows_valid_bulk_void_inflight_payloads(self):
        """allows valid bulk void inflight payloads"""
        data = {
            "transaction_ids": [
                "txn_11111111-1111-4111-8111-111111111111",
                "txn_22222222-2222-4222-8222-222222222222",
            ],
        }

        assert validate_bulk_void_inflight(data) is None

    def test_rejects_empty_transaction_ids_array(self):
        """rejects empty transaction_ids array"""
        assert (
            validate_bulk_void_inflight({"transaction_ids": []})
            == "transaction_ids array cannot be empty."
        )

    def test_rejects_oversized_transaction_ids_array(self):
        """rejects oversized transaction_ids array"""
        transaction_ids = ["txn_test" for _ in range(MAX_BULK_INFLIGHT_ITEMS + 1)]

        assert (
            validate_bulk_void_inflight({"transaction_ids": transaction_ids})
            == f"Too many transaction_ids; max is {MAX_BULK_INFLIGHT_ITEMS}."
        )

    def test_rejects_missing_transaction_id(self):
        """rejects missing transaction_id"""
        assert (
            validate_bulk_void_inflight({"transaction_ids": [""]})
            == "transaction_id is required at index 0."
        )

    def test_allows_skip_queue_on_bulk_void_payloads(self):
        """allows skip_queue on bulk void payloads"""
        data = {
            "skip_queue": True,
            "transaction_ids": ["txn_11111111-1111-4111-8111-111111111111"],
        }

        assert validate_bulk_void_inflight(data) is None

    def test_rejects_invalid_skip_queue_on_bulk_void_payloads(self):
        """rejects invalid skip_queue on bulk void payloads"""
        data = {
            "skip_queue": "true",
            "transaction_ids": ["txn_11111111-1111-4111-8111-111111111111"],
        }

        assert (
            validate_bulk_void_inflight(data)
            == "skip_queue must be a boolean if provided."
        )


class TestRecoverQueue:
    """recoverQueue"""

    def test_allows_valid_threshold_durations(self):
        """allows valid threshold durations"""
        cases = [
            {"threshold": "5m"},
            {"threshold": "1h"},
            {"threshold": "2h45m"},
            {},
        ]
        for data in cases:
            assert validate_recover_queue(data) is None

    def test_rejects_invalid_threshold(self):
        """rejects invalid threshold"""
        assert (
            validate_recover_queue({"threshold": "bogus"})
            == "threshold must be a valid duration string (e.g. 5m, 1h)."
        )
        assert (
            validate_recover_queue({"threshold": ""})
            == "threshold must be a valid duration string (e.g. 5m, 1h)."
        )

    def test_rejects_unknown_fields(self):
        """rejects unknown fields"""
        assert (
            validate_recover_queue({"threshold": "5m", "amount": 1})
            == "Invalid field: amount"
        )
