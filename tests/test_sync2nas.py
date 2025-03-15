import unittest
from unittest.mock import patch, MagicMock, mock_open
import datetime
from sync2nas import (
    initialize_database, reset_sftp_table, search_show_in_db,
    insert_sftp_files_metadata, insert_sftp_temp_files_metadata,
    get_sftp_diffs, create_directory, read_file_to_list
)

class TestSync2NAS(unittest.TestCase):

    @patch('os.makedirs')
    @patch('os.path.exists', return_value=False)
    def test_create_directory(self, mock_exists, mock_makedirs):
        self.assertTrue(create_directory('test/path'))
        mock_makedirs.assert_called_with('test/path')

    @patch('builtins.open', new_callable=mock_open, read_data='line1\nline2')
    def test_read_file_to_list(self, mock_file):
        result = read_file_to_list('dummy_path')
        self.assertEqual(result, ['line1', 'line2'])

    @patch('sqlite3.connect')
    def test_initialize_database(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        result = initialize_database('dummy_db.sqlite')
        self.assertTrue(result)
        mock_conn.cursor().execute.assert_called()

    @patch('sqlite3.connect')
    def test_reset_sftp_table(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        result = reset_sftp_table('dummy_db.sqlite')
        self.assertTrue(result)
        mock_conn.cursor().execute.assert_called()

    @patch('sqlite3.connect')
    def test_insert_sftp_files_metadata(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        sample_data = [{'name': 'file1', 'size': 1234, 'modified_time': datetime.datetime.now(),
                        'path': 'test/file1', 'fetched_at': datetime.datetime.now(), 'is_dir': False}]
        result = insert_sftp_files_metadata(sample_data, 'dummy_db.sqlite')
        self.assertIsNone(result)

    @patch('sqlite3.connect')
    def test_search_show_in_db(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('show1',)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        result = search_show_in_db('show1', 'dummy_db.sqlite')
        self.assertEqual(result, [('show1',)])

    @patch('sqlite3.connect')
    def test_insert_sftp_temp_files_metadata(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        sample_data = [{'name': 'file1', 'size': 1234, 'modified_time': datetime.datetime.now(),
                        'path': 'test/file1', 'fetched_at': datetime.datetime.now(), 'is_dir': False}]
        result = insert_sftp_temp_files_metadata(sample_data, 'dummy_db.sqlite')
        self.assertTrue(result)

    @patch('sqlite3.connect')
    def test_get_sftp_diffs(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'name': 'file1'}]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        result = get_sftp_diffs('dummy_db.sqlite')
        self.assertEqual(result, [{'name': 'file1'}])

if __name__ == '__main__':
    unittest.main()
