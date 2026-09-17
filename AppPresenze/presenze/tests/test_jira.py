from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from presenze.views.jira import _fetch_jira_search_all


def _jira_response(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class TestJiraSearchPagination(SimpleTestCase):
    @patch("presenze.views.jira.requests.get")
    def test_follows_next_page_token_even_after_an_empty_page(self, mocked_get):
        mocked_get.side_effect = [
            _jira_response(
                {
                    "issues": [{"id": "1", "key": "TEST-1"}],
                    "isLast": False,
                    "nextPageToken": "page-2",
                }
            ),
            _jira_response(
                {
                    "issues": [],
                    "isLast": False,
                    "nextPageToken": "page-3",
                }
            ),
            _jira_response(
                {
                    "issues": [{"id": "2", "key": "TEST-2"}],
                    "isLast": True,
                }
            ),
        ]

        payload = _fetch_jira_search_all(
            "example.atlassian.net",
            {"Authorization": "Basic test"},
            "created is not EMPTY",
            ["summary"],
        )

        self.assertEqual([issue["key"] for issue in payload["issues"]], ["TEST-1", "TEST-2"])
        self.assertEqual(payload["total"], 2)
        self.assertEqual(mocked_get.call_count, 3)
        first_params = mocked_get.call_args_list[0].kwargs["params"]
        second_params = mocked_get.call_args_list[1].kwargs["params"]
        third_params = mocked_get.call_args_list[2].kwargs["params"]
        self.assertNotIn("startAt", first_params)
        self.assertEqual(second_params["nextPageToken"], "page-2")
        self.assertEqual(third_params["nextPageToken"], "page-3")

    @patch("presenze.views.jira.requests.get")
    def test_stops_on_a_repeated_token_and_deduplicates_issues(self, mocked_get):
        mocked_get.side_effect = [
            _jira_response(
                {
                    "issues": [{"id": "1", "key": "TEST-1"}],
                    "isLast": False,
                    "nextPageToken": "same-token",
                }
            ),
            _jira_response(
                {
                    "issues": [{"id": "1", "key": "TEST-1"}],
                    "isLast": False,
                    "nextPageToken": "same-token",
                }
            ),
        ]

        payload = _fetch_jira_search_all(
            "example.atlassian.net",
            {},
            "created is not EMPTY",
            ["summary"],
        )

        self.assertEqual([issue["key"] for issue in payload["issues"]], ["TEST-1"])
        self.assertEqual(mocked_get.call_count, 2)
