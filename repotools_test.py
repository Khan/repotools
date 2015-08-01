import repotools
import secrets
import unittest


class TestApiAccess(unittest.TestCase):

    def test_token_works(self):
        """can run authenticated api call"""
        response = repotools.rawktopoke("/user")
        self.assertEquals(200, response.status_code)


if __name__ == '__main__':
    unittest.main()
