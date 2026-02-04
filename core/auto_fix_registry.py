"""
Auto-Fix Registry - PHASE 2 CRITICAL

Pattern-based automatic code/error fixing:
- Common error patterns and their fixes
- Code transformation rules
- Validation of fixes
- Learning from manual fixes
"""
import re
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass
import ast
import traceback


@dataclass
class FixPattern:
    """Pattern and fix for automatic correction"""
    pattern: str  # Regex pattern or error signature
    fix_type: str  # Type of fix (replace, transform, etc)
    fix_action: Any  # Replacement string or transformation function
    validation: Optional[Callable] = None  # Optional validation function
    description: str = ""
    confidence: float = 1.0  # 0.0 to 1.0
    success_count: int = 0
    failure_count: int = 0


class AutoFixRegistry:
    """
    Registry of automatic fixes for common errors

    Learns from manual fixes and applies them automatically
    """

    def __init__(self):
        self.patterns: Dict[str, FixPattern] = {}
        self._register_builtin_fixes()

        # Statistics
        self.stats = {
            'total_attempts': 0,
            'successful_fixes': 0,
            'failed_fixes': 0,
            'patterns_learned': 0
        }

    def _register_builtin_fixes(self):
        """Register common built-in fix patterns"""

        # Unicode encoding errors - replace unicode with ASCII
        self.register_pattern(
            name='unicode_checkmark',
            pattern=r'\\u2713',
            fix_type='replace',
            fix_action='[OK]',
            description='Replace unicode checkmark with [OK]',
            confidence=1.0
        )

        self.register_pattern(
            name='unicode_cross',
            pattern=r'\\u2717',
            fix_type='replace',
            fix_action='[FAIL]',
            description='Replace unicode cross with [FAIL]',
            confidence=1.0
        )

        self.register_pattern(
            name='unicode_bullet',
            pattern=r'\\u2022',
            fix_type='replace',
            fix_action='-',
            description='Replace unicode bullet with dash',
            confidence=1.0
        )

        # Import errors - common wrong imports
        self.register_pattern(
            name='wrong_import_name',
            pattern=r'cannot import name [\'"](\w+)[\'"]',
            fix_type='transform',
            fix_action=self._suggest_import_alternatives,
            description='Suggest alternative import names',
            confidence=0.8
        )

        # Path errors - backslash vs forward slash
        self.register_pattern(
            name='windows_path',
            pattern=r'([A-Za-z]:[/\\][^"\'\s]+)',
            fix_type='transform',
            fix_action=lambda m: m.group(1).replace('\\', '/'),
            description='Normalize Windows paths',
            confidence=0.9
        )

        # Database errors - locked database
        self.register_pattern(
            name='database_locked',
            pattern=r'database is locked',
            fix_type='retry',
            fix_action='retry_with_backoff',
            description='Retry database operation',
            confidence=0.95
        )

        # Indentation errors
        self.register_pattern(
            name='indentation_error',
            pattern=r'IndentationError',
            fix_type='transform',
            fix_action=self._fix_indentation,
            description='Auto-fix indentation',
            confidence=0.7
        )

        # Syntax errors - missing colons
        self.register_pattern(
            name='missing_colon',
            pattern=r'SyntaxError.*expected [\'"]:[\'"]*$',
            fix_type='transform',
            fix_action=self._add_missing_colon,
            description='Add missing colon',
            confidence=0.8
        )

        # Attribute errors - typos
        self.register_pattern(
            name='attribute_typo',
            pattern=r'AttributeError.*has no attribute [\'"](\w+)[\'"]',
            fix_type='transform',
            fix_action=self._suggest_attribute_fix,
            description='Suggest correct attribute name',
            confidence=0.6
        )

        # Type errors - wrong argument count
        self.register_pattern(
            name='wrong_arg_count',
            pattern=r'takes (\d+) .*arguments? but (\d+) .*given',
            fix_type='transform',
            fix_action=self._fix_argument_count,
            description='Fix argument count',
            confidence=0.5
        )

    def register_pattern(self, name: str, pattern: str, fix_type: str,
                        fix_action: Any, description: str = "",
                        confidence: float = 1.0, validation: Callable = None):
        """Register a new fix pattern"""
        self.patterns[name] = FixPattern(
            pattern=pattern,
            fix_type=fix_type,
            fix_action=fix_action,
            validation=validation,
            description=description,
            confidence=confidence
        )

    def try_fix(self, error: Exception, context: dict = None) -> Optional[dict]:
        """
        Try to automatically fix an error

        Returns dict with:
        - fixed: bool
        - fix_applied: str (name of fix)
        - suggestion: str (what to do)
        - confidence: float
        """
        self.stats['total_attempts'] += 1

        error_str = str(error)
        error_type = type(error).__name__

        # Try each pattern
        for name, fix_pattern in self.patterns.items():
            # Check if pattern matches
            if fix_pattern.fix_type == 'retry':
                # Retry-type fixes match on pattern
                if re.search(fix_pattern.pattern, error_str):
                    return self._apply_retry_fix(name, fix_pattern, error, context)

            elif fix_pattern.fix_type == 'replace':
                # Replace-type fixes do string replacement
                match = re.search(fix_pattern.pattern, error_str)
                if match:
                    return self._apply_replace_fix(name, fix_pattern, error, match, context)

            elif fix_pattern.fix_type == 'transform':
                # Transform-type fixes use custom logic
                match = re.search(fix_pattern.pattern, error_str)
                if match:
                    return self._apply_transform_fix(name, fix_pattern, error, match, context)

        # No fix found
        self.stats['failed_fixes'] += 1
        return None

    def _apply_retry_fix(self, name: str, fix_pattern: FixPattern,
                        error: Exception, context: dict) -> dict:
        """Apply a retry-type fix"""
        self.patterns[name].success_count += 1
        self.stats['successful_fixes'] += 1

        return {
            'fixed': False,  # Retry isn't immediate fix
            'fix_applied': name,
            'suggestion': fix_pattern.fix_action,
            'confidence': fix_pattern.confidence,
            'description': fix_pattern.description
        }

    def _apply_replace_fix(self, name: str, fix_pattern: FixPattern,
                          error: Exception, match: re.Match, context: dict) -> dict:
        """Apply a replace-type fix"""
        original = match.group(0)
        replacement = fix_pattern.fix_action

        # Validate if validator provided
        if fix_pattern.validation:
            if not fix_pattern.validation(original, replacement):
                self.patterns[name].failure_count += 1
                self.stats['failed_fixes'] += 1
                return None

        self.patterns[name].success_count += 1
        self.stats['successful_fixes'] += 1

        return {
            'fixed': True,
            'fix_applied': name,
            'suggestion': f"Replace '{original}' with '{replacement}'",
            'confidence': fix_pattern.confidence,
            'description': fix_pattern.description,
            'replacement': replacement
        }

    def _apply_transform_fix(self, name: str, fix_pattern: FixPattern,
                           error: Exception, match: re.Match, context: dict) -> dict:
        """Apply a transform-type fix"""
        try:
            if callable(fix_pattern.fix_action):
                result = fix_pattern.fix_action(match)

                self.patterns[name].success_count += 1
                self.stats['successful_fixes'] += 1

                return {
                    'fixed': True,
                    'fix_applied': name,
                    'suggestion': result if isinstance(result, str) else str(result),
                    'confidence': fix_pattern.confidence,
                    'description': fix_pattern.description
                }
        except Exception as e:
            self.patterns[name].failure_count += 1
            self.stats['failed_fixes'] += 1
            return None

    def _suggest_import_alternatives(self, match: re.Match) -> str:
        """Suggest alternative import names"""
        wrong_name = match.group(1)

        # Common alternatives
        alternatives = {
            'InternetAccess': ['WebSearch', 'BrowserAccess', 'WebBrowser'],
            'DataStorage': ['Database', 'Storage', 'DataStore'],
            'AIModel': ['Model', 'AI', 'LLM'],
        }

        if wrong_name in alternatives:
            suggestions = alternatives[wrong_name]
            return f"Try importing: {', '.join(suggestions)}"

        return f"Check actual class name with grep/find"

    def _fix_indentation(self, match: re.Match) -> str:
        """Suggest indentation fix"""
        return "Use consistent indentation (4 spaces recommended)"

    def _add_missing_colon(self, match: re.Match) -> str:
        """Suggest adding missing colon"""
        return "Add ':' at end of line"

    def _suggest_attribute_fix(self, match: re.Match) -> str:
        """Suggest correct attribute name"""
        wrong_attr = match.group(1)
        return f"Check spelling of '{wrong_attr}' or use dir() to list attributes"

    def _fix_argument_count(self, match: re.Match) -> str:
        """Suggest argument count fix"""
        expected = match.group(1)
        given = match.group(2)
        return f"Function expects {expected} args, but {given} given. Check function signature."

    def learn_from_manual_fix(self, error: Exception, fix_description: str,
                             code_before: str = None, code_after: str = None):
        """
        Learn from a manual fix to create new pattern

        Analyzes what changed and creates a reusable pattern
        """
        error_str = str(error)

        # Generate pattern name
        pattern_name = f"learned_{len(self.patterns)}"

        if code_before and code_after:
            # Analyze code changes
            pattern = self._extract_pattern(code_before, code_after)
            if pattern:
                self.register_pattern(
                    name=pattern_name,
                    pattern=pattern['pattern'],
                    fix_type='replace',
                    fix_action=pattern['replacement'],
                    description=fix_description,
                    confidence=0.7  # Lower confidence for learned patterns
                )
                self.stats['patterns_learned'] += 1
                return True

        # If can't extract pattern, just record the error signature
        self.register_pattern(
            name=pattern_name,
            pattern=re.escape(error_str),
            fix_type='retry',
            fix_action=fix_description,
            description=f"Learned fix: {fix_description}",
            confidence=0.6
        )
        self.stats['patterns_learned'] += 1
        return True

    def _extract_pattern(self, before: str, after: str) -> Optional[dict]:
        """
        Extract a reusable pattern from before/after code

        Tries to find what changed and generalize it
        """
        # Simple diff - find what was replaced
        if len(before) < 200 and len(after) < 200:
            # Find common prefix
            prefix_len = 0
            for i, (c1, c2) in enumerate(zip(before, after)):
                if c1 == c2:
                    prefix_len = i + 1
                else:
                    break

            # Find common suffix
            suffix_len = 0
            for i, (c1, c2) in enumerate(zip(reversed(before), reversed(after))):
                if c1 == c2:
                    suffix_len = i + 1
                else:
                    break

            if prefix_len > 0 or suffix_len > 0:
                changed_before = before[prefix_len:len(before)-suffix_len if suffix_len > 0 else len(before)]
                changed_after = after[prefix_len:len(after)-suffix_len if suffix_len > 0 else len(after)]

                if changed_before and changed_after:
                    return {
                        'pattern': re.escape(changed_before),
                        'replacement': changed_after
                    }

        return None

    def get_stats(self) -> dict:
        """Get comprehensive statistics"""
        pattern_stats = {
            name: {
                'success_count': p.success_count,
                'failure_count': p.failure_count,
                'confidence': p.confidence,
                'success_rate': p.success_count / max(p.success_count + p.failure_count, 1)
            }
            for name, p in self.patterns.items()
        }

        return {
            **self.stats,
            'total_patterns': len(self.patterns),
            'pattern_stats': pattern_stats,
            'fix_success_rate': (self.stats['successful_fixes'] /
                                max(self.stats['total_attempts'], 1))
        }

    def get_best_patterns(self, limit: int = 10) -> List[tuple]:
        """Get best performing patterns"""
        patterns_with_stats = [
            (name, p.success_count / max(p.success_count + p.failure_count, 1))
            for name, p in self.patterns.items()
            if p.success_count + p.failure_count > 0
        ]

        patterns_with_stats.sort(key=lambda x: x[1], reverse=True)
        return patterns_with_stats[:limit]
