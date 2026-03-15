import csv
from typing import Dict, Iterable, List, Set


INVALID_FIELD_CHARS = {"/", "\\", "?", "*", ":", "[", "]"}


def _is_http_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _sanitize_field_name(name: str, fallback: str) -> str:
    cleaned = "".join(ch for ch in name.strip() if ch not in INVALID_FIELD_CHARS)
    if not cleaned:
        cleaned = fallback
    return cleaned[:100]


def _unique_names(names: List[str]) -> List[str]:
    used = set()
    unique = []
    for name in names:
        base = name
        candidate = base
        index = 1
        while candidate in used:
            index += 1
            candidate = f"{base}_{index}"
        used.add(candidate)
        unique.append(candidate[:100])
    return unique


def _prepare_headers(raw_headers: List[str]) -> List[str]:
    sanitized = [_sanitize_field_name(h, f"Column{i + 1}") for i, h in enumerate(raw_headers)]
    return _unique_names(sanitized)


def _iter_csv_rows(
    csv_path: str,
    base_headers: List[str],
    url_indices: Set[int],
) -> Iterable[Dict[str, object]]:
    with open(csv_path, newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        _ = next(reader, None)
        for row in reader:
            if len(row) < len(base_headers):
                row = row + [""] * (len(base_headers) - len(row))
            if len(row) > len(base_headers):
                row = row[: len(base_headers)]

            record: Dict[str, object] = {}
            for index, header in enumerate(base_headers):
                value = row[index]
                if index in url_indices:
                    url_value = value.strip()
                    if _is_http_url(url_value):
                        record[header] = {"text": url_value, "link": url_value}
                    else:
                        continue
                else:
                    record[header] = value
            yield record


def _chunked(items: Iterable[Dict[str, object]], size: int) -> Iterable[List[Dict[str, object]]]:
    batch: List[Dict[str, object]] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _detect_url_indices(csv_path: str, header_count: int) -> Set[int]:
    url_indices: Set[int] = set()
    with open(csv_path, newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        _ = next(reader, None)
        for row in reader:
            if len(url_indices) == header_count:
                break
            limit = min(len(row), header_count)
            for index in range(limit):
                if index in url_indices:
                    continue
                value = row[index].strip()
                if _is_http_url(value):
                    url_indices.add(index)
            if len(url_indices) == header_count:
                break
    return url_indices
