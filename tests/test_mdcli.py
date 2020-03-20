import unittest
from mdlg.mdcli import build_filter_from_option


class TestUtils(unittest.TestCase):
    def test_build_filter_from_option(self):

        TESTS = {
            'test-localized': [('images', 'localized'), ('images', 'localized', None)],
            'test-ID': [('images', 'whatever-image-value'), ('images', 'ID', 'whatever-image-value')],
            'test-fieldname': [('images', 'height==13'), ('images', 'height', '13')],
            'test-ID-list': [('images', 'value-1,value-2'), ('images', 'ID:list', ['value-1', 'value-2'])],
            'test-fieldname-like': [('descriptors', 'classID==*animal*'), ('descriptors', 'classID:like', '%animal%')],
        }

        for name, t in TESTS.items():
            params, exp_results = t
            result = build_filter_from_option(*params)
            for exp, real in zip(exp_results, result):
                self.assertEqual(exp, real)
