# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from io import BytesIO

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.binary import BinaryBytes, BinaryFile, BinaryValue
from odoo.tools.misc import file_open


@tagged('at_install', '-post_install')
class TestBinaryValue(TransactionCase):
    def test_binary_bytes(self):
        data = b'test'
        val = BinaryValue.from_bytes(data)
        self.assertIsInstance(val, BinaryBytes)
        self.assertIs(val.content, data)

        self.assertEqual(val.size, len(data))
        self.assertTrue(val.mimetype, "determine a mimetype")
        self.assertEqual(val.decode(), 'test')
        self.assertEqual(val.to_base64(), b64encode(data).decode())

        self.assertFalse(BinaryValue.from_bytes(b''))

    def test_binary_from_file(self):
        path = 'base/tests/files/file.csv'
        val = BinaryValue.from_file(path)
        self.assertIsInstance(val, BinaryFile)
        self.assertIsInstance(val.content, bytes)
        self.assertEqual(val.decode(), val.content.decode())
        self.assertIsInstance(val.to_base64(), str)

        val2 = BinaryValue.from_file(val.local_path)
        self.assertEqual(val.local_path, val2.local_path)

    def test_binary_open(self):
        data = b'my data'
        val = BinaryValue.from_bytes(data)
        for i in range(1, 3):  # can open multiple times
            with val.open() as f:
                self.assertEqual(f.read(), data, f"Read {i}")

        val = BinaryValue.from_file('base/tests/files/file.csv')
        for i in range(1, 3):  # can open multiple times
            with val.open() as f:
                self.assertEqual(len(f.read()), 18, f"Read {i}")

        data = val.content
        with val.open() as f:
            self.assertIsInstance(f, BytesIO)
            self.assertEqual(f.read(), data)

    def test_binary_file_descriptor(self):
        path = 'base/tests/files/file.csv'
        with file_open(path, 'rb') as f:
            val = BinaryValue.from_file(f.name, reader=f)

            with val.open() as opened:
                self.assertEqual(opened.tell(), 0)
                c1 = opened.read()
                self.assertTrue(c1)
            self.assertFalse(f.closed, "main file stays opened")
            with val.open() as opened:
                self.assertEqual(opened.tell(), 0)
                c2 = opened.read()
                self.assertEqual(c1, c2, "must read the same data")

            with val.open() as fd1, val.open() as fd2:
                self.assertEqual(fd1.read(5), fd2.read(5), "opened files share the position")

            del val  # dereference closes the file
            self.assertTrue(f.closed, "dereference should close the file")

            with self.assertRaises(AssertionError):
                # file must be open
                BinaryValue.from_file(f.name, reader=f)

        with file_open(path, 'rb') as f, self.assertRaises(AssertionError):
            # the path must match
            BinaryValue.from_file(path, reader=f)

        with file_open(path, 'r') as f, self.assertRaises(AssertionError):
            # must be open in binary mode
            BinaryValue.from_file(f.name, reader=f)
