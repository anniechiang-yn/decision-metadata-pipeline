"""Shared helpers for the pipeline scripts.

Purpose: keep settings in one place (config.json) and give every script the same log format.
Input:   config.json in the repository root (run the scripts from the repository root).
Output:  the settings, the namespaces as rdflib Namespace objects, and a configured logger.
"""

import json
import logging
import re
from rdflib import Namespace

CONFIG_FILE = "config.json"

# segment_id format: three-digit conversation number, underscore, three-digit segment number, optional letter
ID_PATTERN = re.compile(r"^\d{3}_\d{3}[a-z]?$")


def load_config(path=CONFIG_FILE):
    """Read config.json and return it as a dictionary."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def namespaces(config):
    """Return the namespaces in config.json as {prefix: Namespace}."""
    return {prefix: Namespace(iri) for prefix, iri in config["namespaces"].items()}


def get_logger(name, log_file=None):
    """Return a logger that writes 'LEVEL message' to the terminal and, if given, to log_file."""
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    if log.handlers:              # already set up in this run
        return log
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode="w", encoding="utf-8"))
    for h in handlers:
        h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        log.addHandler(h)
    return log
