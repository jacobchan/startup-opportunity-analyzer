import hashlib
import uuid
from functools import wraps
from typing import Callable

from src.storage import add_evidence, get_session


def hash_url(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def make_evidence_id() -> str:
    return f"ev-{uuid.uuid4().hex[:12]}"


def evidence_capture(run_id: str, source_type: str = "search"):
    def decorator(func: Callable) -> Callable:
        _seen_hashes: set[str] = set()
        @wraps(func)
        def wrapper(*args, **kwargs) -> str:
            result = func(*args, **kwargs)
            query = str(args[0]) if args else str(kwargs.get("query", ""))
            url_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
            if url_hash not in _seen_hashes:
                _seen_hashes.add(url_hash)
                session = get_session()
                evidence = add_evidence(
                    session=session,
                    run_id=run_id,
                    source_type=source_type,
                    query=query,
                    url=None,
                    title=None,
                    content_excerpt=str(result)[:500],
                    url_hash=url_hash,
                )
                return f"{result}\n\n<!-- evidence_id={evidence.evidence_id} -->"
            return result
        return wrapper
    return decorator
