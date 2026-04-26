"""Vulnerability catalog loader for Jarvis Protocol.

Imports all vulnerability entry modules and builds a VulnerabilityCatalog.
"""

from catalog import VulnerabilityCatalog
from vulnerabilities.nosql_injection import ENTRY as nosql_entry
from vulnerabilities.path_traversal import ENTRY as path_traversal_entry
from vulnerabilities.bola import ENTRY as bola_entry


def load_catalog() -> VulnerabilityCatalog:
    """Load all vulnerability entries and return a populated catalog."""
    return VulnerabilityCatalog(entries=[nosql_entry, path_traversal_entry, bola_entry])
