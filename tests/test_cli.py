"""
Tests for M4B Tools CLI functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import subprocess

from m4b_tools.cli import main, create_parser


class TestCLI:
    """Test the command-line interface."""
    
    def test_parser_creation(self):
        """Test that the parser is created correctly."""
        parser = create_parser()
        assert parser is not None
        
        # Test main help
        help_text = parser.format_help()
        assert "M4B Tools" in help_text
        assert "convert" in help_text
        assert "combine" in help_text
        assert "generate-csv" in help_text
        assert "split" in help_text
    
    def test_convert_parser(self):
        """Test the convert subcommand parser."""
        parser = create_parser()
        
        # Test valid convert arguments
        args = parser.parse_args(['convert', 'pattern', 'output_dir'])
        assert args.command == 'convert'
        assert args.pattern == 'pattern'
        assert args.output_dir == 'output_dir'
        assert args.jobs == 1
        assert not args.flat
        assert not args.progress_bar
    
    def test_combine_parser(self):
        """Test the combine subcommand parser."""
        parser = create_parser()
        
        # Test valid combine arguments
        args = parser.parse_args(['combine', 'pattern', 'output.m4b'])
        assert args.command == 'combine'
        assert args.pattern == 'pattern'
        assert args.output == 'output.m4b'
        assert not args.preserve_chapters
        assert args.csv is None
    
    def test_generate_csv_parser(self):
        """Test the generate-csv subcommand parser."""
        parser = create_parser()
        
        # Test valid generate-csv arguments
        args = parser.parse_args(['generate-csv', 'folder'])
        assert args.command == 'generate-csv'
        assert args.folder == 'folder'
        assert args.output is None
    
    def test_no_command(self):
        """Test behavior when no command is specified."""
        with patch('sys.argv', ['m4b-tools']):
            with patch('builtins.print') as mock_print:
                result = main()
                assert result == 1
    
    @patch('m4b_tools.cli.convert_all_to_m4b')
    def test_convert_command_success(self, mock_convert):
        """Test successful convert command."""
        mock_convert.return_value = (5, 5)  # All files converted successfully
        
        with patch('sys.argv', ['m4b-tools', 'convert', '*.mp3', 'output']):
            with patch('builtins.print') as mock_print:
                result = main()
                assert result == 0
                mock_convert.assert_called_once()
    
    @patch('m4b_tools.cli.convert_all_to_m4b')
    def test_convert_command_partial_failure(self, mock_convert):
        """Test convert command with partial failures."""
        mock_convert.return_value = (3, 5)  # Some files failed
        
        with patch('sys.argv', ['m4b-tools', 'convert', '*.mp3', 'output']):
            with patch('builtins.print') as mock_print:
                result = main()
                assert result == 0  # Partial success still returns 0
                mock_convert.assert_called_once()
    
    @patch('m4b_tools.cli.combine_m4b_files')
    def test_combine_command_success(self, mock_combine):
        """Test successful combine command."""
        mock_combine.return_value = True
        
        with patch('sys.argv', ['m4b-tools', 'combine', '*.m4b', 'output.m4b']):
            with patch('builtins.print') as mock_print:
                result = main()
                assert result == 0
                mock_combine.assert_called_once()
    
    @patch('m4b_tools.cli.combine_m4b_files')
    def test_combine_command_failure(self, mock_combine):
        """Test failed combine command."""
        mock_combine.return_value = False
        
        with patch('sys.argv', ['m4b-tools', 'combine', '*.m4b', 'output.m4b']):
            with patch('builtins.print') as mock_print:
                result = main()
                assert result == 1
                mock_combine.assert_called_once()
    
    @patch('m4b_tools.cli.generate_csv_from_folder')
    def test_generate_csv_command_success(self, mock_generate):
        """Test successful generate-csv command."""
        mock_generate.return_value = True
        
        with patch('sys.argv', ['m4b-tools', 'generate-csv', 'folder']):
            with patch('builtins.print') as mock_print:
                result = main()
                assert result == 0
                mock_generate.assert_called_once()
    
    def test_keyboard_interrupt(self):
        """Test handling of keyboard interrupt."""
        with patch('m4b_tools.cli.convert_all_to_m4b') as mock_convert:
            mock_convert.side_effect = KeyboardInterrupt()
            
            with patch('sys.argv', ['m4b-tools', 'convert', '*.mp3', 'output']):
                with patch('builtins.print') as mock_print:
                    result = main()
                    assert result == 130
    
    def test_split_parser(self):
        """Test the split subcommand parser."""
        parser = create_parser()
        
        # Test valid split arguments
        args = parser.parse_args(['split', 'test.m4b', './output'])
        assert args.command == 'split'
        assert args.pattern == 'test.m4b'
        assert args.output_dir == './output'
        assert args.format == 'mp3'  # Default format
        assert args.jobs == 1  # Default jobs
        
        # Test with optional arguments
        args = parser.parse_args(['split', '*.m4b', './out', '--format', 'm4a', '--template', 'custom', '-j', '4'])
        assert args.format == 'm4a'
        assert args.template == 'custom'
        assert args.jobs == 4
    
    def test_split_command_help(self):
        """Test split command help text."""
        result = subprocess.run(['python', '-m', 'm4b_tools.cli', 'split', '--help'], 
                              capture_output=True, text=True)
        assert result.returncode == 0
        assert 'Split a single M4B file by chapters to MP3' in result.stdout
        assert '--format' in result.stdout
        assert '--template' in result.stdout
        assert '--jobs' in result.stdout
    
    def test_split_command_arguments(self):
        """Test split command argument parsing."""
        parser = create_parser()
        
        # Test basic arguments
        args = parser.parse_args(['split', 'test.m4b', './output'])
        assert args.command == 'split'
        assert args.pattern == 'test.m4b'
        assert args.output_dir == './output'
        assert args.format == 'mp3'  # default
        assert args.jobs == 1  # default
        
        # Test with options
        args = parser.parse_args(['split', '*.m4b', './out', '--format', 'm4a', '--jobs', '4'])
        assert args.format == 'm4a'
        assert args.jobs == 4
        
        # Test custom template
        template = '{author}/{book_title}/Chapter {chapter_num:02d}.{ext}'
        args = parser.parse_args(['split', 'book.m4b', './output', '--template', template])
        assert args.template == template