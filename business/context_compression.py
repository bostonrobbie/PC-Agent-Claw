#!/usr/bin/env python3
"""Automatic Context Compression (#26) - Compress context to save tokens"""
from typing import List, Dict
import sys
from pathlib import Path
import re

sys.path.append(str(Path(__file__).parent.parent))

class ContextCompressor:
    """Compress conversation context to save tokens while preserving meaning"""

    def __init__(self):
        self.compression_strategies = {
            'remove_redundancy': self._remove_redundant_content,
            'summarize_code': self._summarize_code_blocks,
            'abbreviate': self._abbreviate_common_terms,
            'remove_formatting': self._remove_extra_formatting
        }

    def compress(self, text: str, target_reduction: float = 0.3) -> str:
        """
        Compress text while preserving meaning

        Args:
            text: Text to compress
            target_reduction: Target reduction percentage (0.3 = 30% reduction)

        Returns:
            Compressed text
        """
        original_length = len(text)
        compressed = text

        # Apply compression strategies in order
        for strategy_name, strategy_func in self.compression_strategies.items():
            compressed = strategy_func(compressed)

            # Check if we've hit target
            current_reduction = 1 - (len(compressed) / original_length)
            if current_reduction >= target_reduction:
                break

        return compressed

    def _remove_redundant_content(self, text: str) -> str:
        """Remove redundant or repetitive content"""
        # Remove repeated newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove repeated spaces
        text = re.sub(r' {2,}', ' ', text)

        # Remove common filler phrases
        fillers = [
            r'\bas you can see\b',
            r'\bas mentioned\b',
            r'\bit should be noted that\b',
            r'\bit is worth noting that\b'
        ]
        for filler in fillers:
            text = re.sub(filler, '', text, flags=re.IGNORECASE)

        return text.strip()

    def _summarize_code_blocks(self, text: str) -> str:
        """Summarize long code blocks"""
        # Find code blocks
        code_pattern = r'```[\s\S]*?```'

        def summarize_block(match):
            block = match.group(0)
            lines = block.split('\n')

            # If code block is short, keep it
            if len(lines) <= 15:
                return block

            # Extract key parts: first few lines, last few lines, function signatures
            first_lines = '\n'.join(lines[:5])
            last_lines = '\n'.join(lines[-3:])

            # Count omitted lines
            omitted = len(lines) - 8

            return f"{first_lines}\n... ({omitted} lines omitted) ...\n{last_lines}"

        return re.sub(code_pattern, summarize_block, text)

    def _abbreviate_common_terms(self, text: str) -> str:
        """Abbreviate common technical terms"""
        abbreviations = {
            r'\bJavaScript\b': 'JS',
            r'\bTypeScript\b': 'TS',
            r'\bPython\b': 'Py',
            r'\bapplication\b': 'app',
            r'\bdatabase\b': 'DB',
            r'\bconfiguration\b': 'config',
            r'\benvironment\b': 'env',
            r'\brepository\b': 'repo',
            r'\bdocumentation\b': 'docs',
            r'\bparameter\b': 'param',
            r'\bargument\b': 'arg'
        }

        for full_term, abbrev in abbreviations.items():
            text = re.sub(full_term, abbrev, text, flags=re.IGNORECASE)

        return text

    def _remove_extra_formatting(self, text: str) -> str:
        """Remove excessive formatting"""
        # Remove horizontal rules
        text = re.sub(r'-{3,}', '', text)
        text = re.sub(r'={3,}', '', text)

        # Simplify lists
        text = re.sub(r'^\s*[-*+]\s+', '- ', text, flags=re.MULTILINE)

        return text

    def compress_conversation(self, messages: List[Dict]) -> List[Dict]:
        """Compress a list of conversation messages"""
        compressed_messages = []

        for msg in messages:
            compressed_msg = msg.copy()

            if 'content' in msg:
                compressed_msg['content'] = self.compress(msg['content'])

            compressed_messages.append(compressed_msg)

        return compressed_messages

    def get_compression_stats(self, original: str, compressed: str) -> Dict:
        """Get statistics about compression"""
        original_length = len(original)
        compressed_length = len(compressed)
        reduction = 1 - (compressed_length / original_length)

        return {
            'original_length': original_length,
            'compressed_length': compressed_length,
            'reduction_pct': round(reduction * 100, 2),
            'tokens_saved_est': int((original_length - compressed_length) / 4)  # Rough estimate
        }


if __name__ == '__main__':
    # Test the compressor
    compressor = ContextCompressor()

    sample_text = """
    As you can see, this is a sample text that contains some redundant content.



    It should be noted that we have multiple blank lines here.

    Here is a JavaScript application that does something:

    ```python
    def example_function():
        # This is a very long code block
        line1 = "content"
        line2 = "content"
        line3 = "content"
        line4 = "content"
        line5 = "content"
        line6 = "content"
        line7 = "content"
        line8 = "content"
        line9 = "content"
        line10 = "content"
        line11 = "content"
        line12 = "content"
        line13 = "content"
        line14 = "content"
        line15 = "content"
        line16 = "content"
        line17 = "content"
        line18 = "content"
        line19 = "content"
        line20 = "content"
        return "done"
    ```

    The configuration file for the environment is in the repository documentation.
    """

    compressed = compressor.compress(sample_text)
    stats = compressor.get_compression_stats(sample_text, compressed)

    print("Context Compression System ready!")
    print(f"\nCompression stats:")
    print(f"  Original: {stats['original_length']} chars")
    print(f"  Compressed: {stats['compressed_length']} chars")
    print(f"  Reduction: {stats['reduction_pct']}%")
    print(f"  Estimated tokens saved: {stats['tokens_saved_est']}")
