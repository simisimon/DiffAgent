"""
Rule-based baseline for configuration validation.
Uses pattern matching and heuristics to detect common misconfigurations.
"""

import re
from typing import List, Dict, Any


class RuleBasedValidator:
    """Baseline that uses predefined rules to detect configuration errors."""

    def __init__(self):
        self.rules = [
            self._check_debug_mode,
            self._check_exposed_secrets,
            self._check_wildcard_hosts,
            self._check_insecure_ports,
            self._check_missing_quotes,
            self._check_port_conflicts,
            self._check_memory_limits,
        ]

    def validate(self, diff_content: str) -> Dict[str, Any]:
        """
        Validate configuration changes using rule-based patterns.

        Args:
            diff_content: Git diff content

        Returns:
            Dictionary with has_errors, errors list, and summary
        """
        errors = []

        # Parse diff to extract changes
        changes = self._parse_diff(diff_content)

        # Apply each rule
        for rule in self.rules:
            rule_errors = rule(changes, diff_content)
            errors.extend(rule_errors)

        return {
            "has_errors": len(errors) > 0,
            "errors": errors,
            "summary": f"Found {len(errors)} potential issues using rule-based validation"
        }

    def _parse_diff(self, diff_content: str) -> List[Dict[str, Any]]:
        """Parse git diff to extract file changes."""
        changes = []
        current_file = None

        for line in diff_content.split('\n'):
            # Track current file
            if line.startswith('diff --git'):
                parts = line.split()
                if len(parts) >= 4:
                    current_file = parts[3].lstrip('b/')

            # Extract added lines
            elif line.startswith('+') and not line.startswith('+++'):
                if current_file:
                    changes.append({
                        'file': current_file,
                        'line': line[1:].strip(),
                        'type': 'added'
                    })

            # Extract removed lines
            elif line.startswith('-') and not line.startswith('---'):
                if current_file:
                    changes.append({
                        'file': current_file,
                        'line': line[1:].strip(),
                        'type': 'removed'
                    })

        return changes

    def _check_debug_mode(self, changes: List[Dict], diff: str) -> List[Dict[str, Any]]:
        """Check for DEBUG=True in production configs."""
        errors = []

        for change in changes:
            if change['type'] == 'added':
                line = change['line']
                # Check for DEBUG=True, DEBUG=1, debug: true, etc.
                if re.search(r'DEBUG\s*[=:]\s*(True|true|1|yes)', line, re.IGNORECASE):
                    errors.append({
                        'file_path': change['file'],
                        'option_name': 'DEBUG',
                        'severity': 'critical',
                        'reason': 'DEBUG mode is enabled, which can expose sensitive information in production',
                        'suggested_fix': 'Set DEBUG=False or remove debug flag'
                    })

        return errors

    def _check_exposed_secrets(self, changes: List[Dict], diff: str) -> List[Dict[str, Any]]:
        """Check for exposed API keys, passwords, tokens."""
        errors = []
        secret_patterns = [
            (r'API_KEY\s*[=:]\s*["\']?[a-zA-Z0-9]{20,}', 'API_KEY'),
            (r'SECRET_KEY\s*[=:]\s*["\']?[a-zA-Z0-9]{20,}', 'SECRET_KEY'),
            (r'PASSWORD\s*[=:]\s*["\']?[^\s"\']+', 'PASSWORD'),
            (r'TOKEN\s*[=:]\s*["\']?[a-zA-Z0-9]{20,}', 'TOKEN'),
        ]

        for change in changes:
            if change['type'] == 'added':
                line = change['line']
                for pattern, name in secret_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Exclude environment variable references like ${VAR}
                        if '${' not in line and '$(' not in line:
                            errors.append({
                                'file_path': change['file'],
                                'option_name': name,
                                'severity': 'critical',
                                'reason': f'Potential hardcoded {name} detected',
                                'suggested_fix': f'Use environment variables or secrets management for {name}'
                            })

        return errors

    def _check_wildcard_hosts(self, changes: List[Dict], diff: str) -> List[Dict[str, Any]]:
        """Check for wildcard in ALLOWED_HOSTS or CORS settings."""
        errors = []

        for change in changes:
            if change['type'] == 'added':
                line = change['line']
                if re.search(r'ALLOWED_HOSTS\s*[=:]\s*\[.*[\'"]\*[\'"].*\]', line):
                    errors.append({
                        'file_path': change['file'],
                        'option_name': 'ALLOWED_HOSTS',
                        'severity': 'critical',
                        'reason': 'Wildcard (*) in ALLOWED_HOSTS allows requests from any domain',
                        'suggested_fix': 'Specify explicit domain names instead of using wildcard'
                    })

                if re.search(r'CORS.*ORIGIN.*[\'"]\*[\'"]', line, re.IGNORECASE):
                    errors.append({
                        'file_path': change['file'],
                        'option_name': 'CORS_ORIGIN',
                        'severity': 'warning',
                        'reason': 'Wildcard in CORS origin allows requests from any domain',
                        'suggested_fix': 'Specify explicit origins for CORS'
                    })

        return errors

    def _check_insecure_ports(self, changes: List[Dict], diff: str) -> List[Dict[str, Any]]:
        """Check for services running on privileged ports without proper context."""
        errors = []

        for change in changes:
            if change['type'] == 'added':
                line = change['line']
                # Check for EXPOSE or PORT settings with privileged ports
                match = re.search(r'(EXPOSE|PORT)\s+(\d+)', line, re.IGNORECASE)
                if match:
                    port = int(match.group(2))
                    if port < 1024 and port != 80 and port != 443:
                        errors.append({
                            'file_path': change['file'],
                            'option_name': match.group(1),
                            'severity': 'warning',
                            'reason': f'Using privileged port {port} may require root privileges',
                            'suggested_fix': f'Consider using port {port + 8000} or run with proper capabilities'
                        })

        return errors

    def _check_missing_quotes(self, changes: List[Dict], diff: str) -> List[Dict[str, Any]]:
        """Check for values that should be quoted (e.g., version numbers)."""
        errors = []

        for change in changes:
            if change['type'] == 'added' and change['file'].endswith(('.yaml', '.yml')):
                line = change['line']
                # Check for unquoted version numbers in YAML
                if re.search(r'version\s*:\s*\d+\.\d+', line, re.IGNORECASE):
                    errors.append({
                        'file_path': change['file'],
                        'option_name': 'version',
                        'severity': 'info',
                        'reason': 'Version numbers in YAML should be quoted to preserve formatting',
                        'suggested_fix': 'Add quotes around version number (e.g., version: "1.0")'
                    })

        return errors

    def _check_port_conflicts(self, changes: List[Dict], diff: str) -> List[Dict[str, Any]]:
        """Check for potential port conflicts across files."""
        errors = []
        port_mappings = {}

        # Collect all port definitions
        for change in changes:
            if change['type'] == 'added':
                line = change['line']
                # Match various port patterns
                port_match = re.search(r'(PORT|port|EXPOSE)\s*[=:]\s*(\d+)', line)
                if port_match:
                    port = port_match.group(2)
                    if port in port_mappings and port_mappings[port] != change['file']:
                        errors.append({
                            'file_path': change['file'],
                            'option_name': 'PORT',
                            'severity': 'warning',
                            'reason': f'Port {port} is defined in multiple files: {change["file"]} and {port_mappings[port]}',
                            'suggested_fix': 'Ensure port numbers are consistent across configuration files'
                        })
                    port_mappings[port] = change['file']

        return errors

    def _check_memory_limits(self, changes: List[Dict], diff: str) -> List[Dict[str, Any]]:
        """Check for unrealistic memory or resource limits."""
        errors = []

        for change in changes:
            if change['type'] == 'added':
                line = change['line']
                # Check for very large memory allocations (e.g., >16GB)
                mem_match = re.search(r'(memory|MEMORY|mem)[_\-]?(limit|max)\s*[=:]\s*(\d+)(g|G|gb|GB)', line)
                if mem_match:
                    size = int(mem_match.group(3))
                    if size > 16:
                        errors.append({
                            'file_path': change['file'],
                            'option_name': 'memory_limit',
                            'severity': 'warning',
                            'reason': f'Memory limit of {size}GB seems unusually high',
                            'suggested_fix': 'Verify memory limit is intentional and resources are available'
                        })

        return errors
