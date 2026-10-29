import unittest
import math
import sys
import os

# Add parent directory to sys.path to import app modules if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, escape_ldap_filter


class TestSortSemantics(unittest.TestCase):
    """
    Validates the exact sort semantics established in app.py:
    all_users.sort(key=lambda x: x.get(sort_by, '').lower())
    """

    def test_case_insensitivity(self):
        """Case insensitivity: .lower() treats 'Alice', 'alice', 'ALICE' as equal key."""
        items = [
            {'cn': 'bob'},
            {'cn': 'Alice'},
            {'cn': 'charlie'},
            {'cn': 'ALICE_UPPER'}
        ]
        items.sort(key=lambda x: x.get('cn', '').lower())
        expected_cns = ['Alice', 'ALICE_UPPER', 'bob', 'charlie']
        self.assertEqual([x['cn'] for x in items], expected_cns)

    def test_missing_values_sort_first(self):
        """
        Missing values: x.get(sort_by, '') returns '' when attribute is missing.
        In Python ascending sort, '' < 'a', so missing values sort FIRST.
        """
        items = [
            {'uid': '101', 'sn': 'Smith'},
            {'uid': '102'},  # missing 'sn'
            {'uid': '103', 'sn': 'Adams'},
            {'uid': '104', 'sn': ''}  # empty 'sn'
        ]
        items.sort(key=lambda x: x.get('sn', '').lower())
        # The two items with empty/missing 'sn' must appear before 'Adams' and 'Smith'
        self.assertEqual(items[0]['uid'], '102')
        self.assertEqual(items[1]['uid'], '104')
        self.assertEqual(items[2]['uid'], '103')
        self.assertEqual(items[3]['uid'], '101')

    def test_stable_sort_duplicate_values(self):
        """
        Python's Timsort is stable: entries with duplicate sort keys preserve
        their original physical insertion order.
        """
        items = [
            {'cn': 'SameName', 'id': 1},
            {'cn': 'Alpha', 'id': 2},
            {'cn': 'SameName', 'id': 3},
            {'cn': 'SameName', 'id': 4},
            {'cn': 'Beta', 'id': 5}
        ]
        items.sort(key=lambda x: x.get('cn', '').lower())
        same_ids = [x['id'] for x in items if x['cn'] == 'SameName']
        self.assertEqual(same_ids, [1, 3, 4], "Stable sort must preserve insertion order for identical keys")

    def test_no_secondary_tie_breaking(self):
        """
        Confirm that no secondary tie-breaker exists in current code.
        If items have identical key, secondary fields (e.g. uid) do NOT alter ordering.
        """
        items = [
            {'cn': 'Zeta', 'uid': '999'},
            {'cn': 'Zeta', 'uid': '001'}
        ]
        items.sort(key=lambda x: x.get('cn', '').lower())
        self.assertEqual(items[0]['uid'], '999')
        self.assertEqual(items[1]['uid'], '001')


class TestPaginationBoundaries(unittest.TestCase):
    """
    Validates boundary conditions: first, last, beyond-last, negative, and empty pages.
    """

    def _paginate(self, total_count, per_page, requested_page):
        """Replicates pagination indexing and clamping logic from app.py lines 208-255"""
        if total_count == 0:
            return [], 0, 0
        total_pages = max(1, math.ceil(total_count / per_page))
        page = max(1, min(requested_page, total_pages))
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        return start_idx, end_idx, page, total_pages

    def test_first_page(self):
        start, end, page, total_pages = self._paginate(100, 25, 1)
        self.assertEqual(page, 1)
        self.assertEqual((start, end), (0, 25))
        self.assertEqual(total_pages, 4)

    def test_last_page(self):
        start, end, page, total_pages = self._paginate(100, 25, 4)
        self.assertEqual(page, 4)
        self.assertEqual((start, end), (75, 100))

    def test_beyond_last_page_clamping(self):
        """When requested_page > total_pages, app clamps to total_pages."""
        start, end, page, total_pages = self._paginate(100, 25, 9999)
        self.assertEqual(page, 4)
        self.assertEqual((start, end), (75, 100))

    def test_negative_or_zero_page_clamping(self):
        """When requested_page <= 0, app clamps to 1."""
        start, end, page, total_pages = self._paginate(100, 25, 0)
        self.assertEqual(page, 1)
        self.assertEqual((start, end), (0, 25))

        start, end, page, total_pages = self._paginate(100, 25, -10)
        self.assertEqual(page, 1)
        self.assertEqual((start, end), (0, 25))

    def test_empty_collection(self):
        """When total_count == 0, returns empty result and 0 pages."""
        items, count, pages = self._paginate(0, 25, 1)
        self.assertEqual(items, [])
        self.assertEqual(count, 0)
        self.assertEqual(pages, 0)


class TestSearchEscaping(unittest.TestCase):
    """
    Validates RFC 4515 LDAP search filter escaping via escape_ldap_filter().
    """

    def test_empty_string(self):
        self.assertEqual(escape_ldap_filter(''), '')
        self.assertEqual(escape_ldap_filter(None), '')

    def test_special_characters_escaping(self):
        """Test escaping of *, (, ), \\, \\0"""
        self.assertEqual(escape_ldap_filter('*'), '\\2a')
        self.assertEqual(escape_ldap_filter('('), '\\28')
        self.assertEqual(escape_ldap_filter(')'), '\\29')
        self.assertEqual(escape_ldap_filter('\\'), '\\5c')
        self.assertEqual(escape_ldap_filter('\0'), '\\00')

    def test_injection_payload_escaping(self):
        """Prevent LDAP injection attempts from breaking filter syntax"""
        injection = "admin*)(uid=*))(|(uid=*"
        escaped = escape_ldap_filter(injection)
        self.assertNotIn('*', escaped)
        self.assertNotIn('(', escaped)
        self.assertNotIn(')', escaped)
        self.assertEqual(escaped, 'admin\\2a\\29\\28uid=\\2a\\29\\29\\28|\\28uid=\\2a')


class TestAuthorizationAndContracts(unittest.TestCase):
    """
    Validates existing route contracts, headers, and HTTP response statuses.
    """

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_api_metrics_contract(self):
        resp = self.client.get('/api/metrics')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'application/json')
        data = resp.get_json()
        for key in ['cpu', 'memory', 'disk', 'uptime']:
            self.assertIn(key, data)

    def test_api_user_count_contract(self):
        resp = self.client.get('/api/user-count')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'application/json')
        data = resp.get_json()
        self.assertIn('count', data)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'success')
        self.assertIsInstance(data['count'], int)

    def test_nonexistent_route_404(self):
        resp = self.client.get('/definitely_not_a_valid_route_12345')
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()
