#!/usr/bin/env python3
"""Freeze one accepted YAM record for every original source-manifest slot."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


SOURCE_PATTERN = re.compile(r"source_(\d+)$")


@dataclass(frozen=True)
class Candidate:
    source_index: int
    original_slot: int
    record_dir: Path
    target_uuid: str
    source_policy_shard: str

    @property
    def kind(self) -> str:
        return "original" if self.source_index == self.original_slot else "replacement"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-root", type=Path, required=True)
    parser.add_argument("--base-source-manifest", type=Path, required=True)
    parser.add_argument("--replacement-source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _manifest_rows(path: Path) -> list[dict[str, object]]:
    payload = _read_json(path)
    rows = payload.get("shards")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Expected a shards list in {path}")
    return rows


def _replacement_slot_map(path: Path, base_count: int) -> dict[int, int]:
    payload = _read_json(path)
    rows = payload.get("shards")
    if not isinstance(rows, list) or len(rows) < base_count:
        raise ValueError(f"Replacement manifest has fewer than {base_count} rows: {path}")
    provenance = payload.get("replacement_provenance")
    if not isinstance(provenance, list):
        raise ValueError(f"Missing replacement_provenance in {path}")

    mapping: dict[int, int] = {}
    for row in provenance:
        if not isinstance(row, dict):
            raise ValueError(f"Malformed replacement provenance row in {path}")
        source_index = int(row["new_source_index"])
        original_slot = int(row["excluded_source_index"])
        if source_index < base_count:
            raise ValueError(f"Replacement index overlaps original range: {source_index}")
        if not 0 <= original_slot < base_count:
            raise ValueError(f"Replacement slot outside original range: {original_slot}")
        previous = mapping.setdefault(source_index, original_slot)
        if previous != original_slot:
            raise ValueError(
                f"Replacement {source_index} maps to conflicting slots {previous} and {original_slot}"
            )
    return mapping


def _metadata_path(record_dir: Path, source_index: int) -> Path | None:
    padded = f"{source_index:06d}"
    expected = record_dir / "policy_dataset" / f"yam_rgb_policy_{padded}" / "metadata.json"
    if expected.is_file():
        return expected
    matches = sorted((record_dir / "policy_dataset").glob("yam_rgb_policy_*/metadata.json"))
    if len(matches) > 1:
        raise ValueError(f"Multiple policy metadata files under {record_dir}")
    return matches[0] if matches else None


def discover_candidates(
    records_root: Path,
    *,
    base_count: int,
    replacement_slots: dict[int, int],
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for record_dir in sorted(records_root.glob("source_*")):
        match = SOURCE_PATTERN.fullmatch(record_dir.name)
        if match is None or not record_dir.is_dir():
            continue
        source_index = int(match.group(1))
        metadata_path = _metadata_path(record_dir, source_index)
        if metadata_path is None:
            continue
        if source_index < base_count:
            original_slot = source_index
        elif source_index in replacement_slots:
            original_slot = replacement_slots[source_index]
        else:
            raise ValueError(f"Accepted source {source_index} has no replacement provenance")
        metadata = _read_json(metadata_path)
        target_uuid = str(metadata.get("target_uuid") or "").strip()
        source_policy_shard = str(metadata.get("source_policy_shard") or "").strip()
        if not target_uuid or not source_policy_shard:
            raise ValueError(f"Missing target/source-policy metadata in {metadata_path}")
        candidates.append(
            Candidate(
                source_index=source_index,
                original_slot=original_slot,
                record_dir=Path(os.path.abspath(record_dir)),
                target_uuid=target_uuid,
                source_policy_shard=source_policy_shard,
            )
        )
    return candidates


def _maximum_new_uuid_assignment(
    candidates_by_slot: dict[int, list[Candidate]],
    represented_uuids: set[str],
) -> dict[int, str]:
    adjacency = {
        slot: sorted({candidate.target_uuid for candidate in candidates if candidate.target_uuid not in represented_uuids})
        for slot, candidates in candidates_by_slot.items()
    }
    uuid_to_slot: dict[str, int] = {}

    def assign(slot: int, seen: set[str]) -> bool:
        for target_uuid in adjacency[slot]:
            if target_uuid in seen:
                continue
            seen.add(target_uuid)
            previous_slot = uuid_to_slot.get(target_uuid)
            if previous_slot is None or assign(previous_slot, seen):
                uuid_to_slot[target_uuid] = slot
                return True
        return False

    for slot in sorted(adjacency, key=lambda value: (len(adjacency[value]), value)):
        assign(slot, set())
    return {slot: target_uuid for target_uuid, slot in uuid_to_slot.items()}


def select_candidates(candidates: list[Candidate], base_count: int) -> list[Candidate]:
    candidates_by_slot: dict[int, list[Candidate]] = {slot: [] for slot in range(base_count)}
    for candidate in candidates:
        candidates_by_slot[candidate.original_slot].append(candidate)
    missing = [slot for slot, rows in candidates_by_slot.items() if not rows]
    if missing:
        preview = ",".join(str(slot) for slot in missing[:20])
        raise ValueError(f"No accepted record for {len(missing)} original slots: {preview}")

    selected: dict[int, Candidate] = {}
    source_policy_counts: Counter[str] = Counter()
    represented_uuids: set[str] = set()
    replacement_slots: dict[int, list[Candidate]] = {}
    for slot, rows in candidates_by_slot.items():
        originals = [candidate for candidate in rows if candidate.source_index == slot]
        if originals:
            chosen = min(originals, key=lambda candidate: candidate.source_index)
            selected[slot] = chosen
            source_policy_counts[chosen.source_policy_shard] += 1
            represented_uuids.add(chosen.target_uuid)
        else:
            replacement_slots[slot] = rows

    uuid_assignment = _maximum_new_uuid_assignment(replacement_slots, represented_uuids)
    for slot in sorted(replacement_slots):
        rows = replacement_slots[slot]
        assigned_uuid = uuid_assignment.get(slot)
        pool = [candidate for candidate in rows if candidate.target_uuid == assigned_uuid] if assigned_uuid else rows
        chosen = min(
            pool,
            key=lambda candidate: (
                candidate.target_uuid in represented_uuids,
                source_policy_counts[candidate.source_policy_shard],
                candidate.source_index,
            ),
        )
        selected[slot] = chosen
        source_policy_counts[chosen.source_policy_shard] += 1
        represented_uuids.add(chosen.target_uuid)
    return [selected[slot] for slot in range(base_count)]


def _selection_report(
    *,
    selected: list[Candidate],
    all_candidates: list[Candidate],
    base_manifest: Path,
    replacement_manifest: Path,
    records_root: Path,
) -> dict[str, object]:
    candidate_counts = Counter(candidate.original_slot for candidate in all_candidates)
    source_policy_counts = Counter(candidate.source_policy_shard for candidate in selected)
    reused_counts = [count for count in source_policy_counts.values() if count > 1]
    return {
        "base_source_manifest": str(base_manifest),
        "replacement_source_manifest": str(replacement_manifest),
        "records_root": str(records_root),
        "accepted_candidate_count": len(all_candidates),
        "selected_count": len(selected),
        "selected_original_count": sum(candidate.kind == "original" for candidate in selected),
        "selected_replacement_count": sum(candidate.kind == "replacement" for candidate in selected),
        "discarded_duplicate_count": len(all_candidates) - len(selected),
        "unique_target_uuid_count": len({candidate.target_uuid for candidate in selected}),
        "unique_source_policy_shard_count": len(source_policy_counts),
        "reused_source_policy_shard_count": len(reused_counts),
        "rows_on_reused_source_policy_shards": sum(reused_counts),
        "max_source_policy_shard_reuse": max(source_policy_counts.values(), default=0),
        "rows": [
            {
                "original_slot": candidate.original_slot,
                "selected_source_index": candidate.source_index,
                "kind": candidate.kind,
                "target_uuid": candidate.target_uuid,
                "source_policy_shard": candidate.source_policy_shard,
                "record_dir": str(candidate.record_dir),
                "accepted_candidate_count_for_slot": candidate_counts[candidate.original_slot],
            }
            for candidate in selected
        ],
    }


def freeze_records(
    *,
    records_root: Path,
    base_source_manifest: Path,
    replacement_source_manifest: Path,
    output_dir: Path,
) -> dict[str, object]:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    base_count = len(_manifest_rows(base_source_manifest))
    replacement_slots = _replacement_slot_map(replacement_source_manifest, base_count)
    candidates = discover_candidates(
        records_root,
        base_count=base_count,
        replacement_slots=replacement_slots,
    )
    selected = select_candidates(candidates, base_count)
    report = _selection_report(
        selected=selected,
        all_candidates=candidates,
        base_manifest=base_source_manifest,
        replacement_manifest=replacement_source_manifest,
        records_root=records_root,
    )

    temporary = output_dir.with_name(f".{output_dir.name}.tmp.{os.getpid()}")
    if temporary.exists():
        shutil.rmtree(temporary)
    records_dir = temporary / "records"
    records_dir.mkdir(parents=True)
    try:
        for candidate in selected:
            os.symlink(candidate.record_dir, records_dir / candidate.record_dir.name)
        (temporary / "selection.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, output_dir)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return report


def main() -> None:
    args = _parser().parse_args()
    report = freeze_records(
        records_root=args.records_root,
        base_source_manifest=args.base_source_manifest,
        replacement_source_manifest=args.replacement_source_manifest,
        output_dir=args.output_dir,
    )
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, sort_keys=True))


if __name__ == "__main__":
    main()
