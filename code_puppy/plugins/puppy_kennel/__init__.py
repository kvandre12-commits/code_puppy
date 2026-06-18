"""Puppy Kennel — local-first context cache for Code Puppy.

A kennel is not AI memory; it is a local context object used to rebuild working
context cheaply. Inspired by MemKennel's wings -> rooms -> drawers model, but
backed by SQLite + FTS5 instead of ChromaDB. No daemon, no API key, no cloud,
multi-process safe via WAL mode.
"""
