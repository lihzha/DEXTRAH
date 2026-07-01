#!/usr/bin/env bash
set -euo pipefail

output_dir="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
mkdir -p "$output_dir"

asset_ids=(
  dark_wood
  fine_grained_wood
  kitchen_wood
  laminate_floor
  laminate_floor_02
  oak_veneer_01
  plank_flooring
  plank_flooring_03
  plywood
  rosewood_veneer1
  stained_pine
  wood_floor
  wood_table
  wood_table_worn
)

manifest_tmp="$(mktemp)"
trap 'rm -f "$manifest_tmp"' EXIT
printf 'asset_id\tfile\tmd5\turl\n' >"$manifest_tmp"

for asset_id in "${asset_ids[@]}"; do
  files_json="$(curl -fsSL --retry 4 "https://api.polyhaven.com/files/${asset_id}")"
  url="$(jq -er '.Diffuse["1k"].jpg.url' <<<"$files_json")"
  expected_md5="$(jq -er '.Diffuse["1k"].jpg.md5' <<<"$files_json")"
  output_path="$output_dir/${asset_id}_diff_1k.jpg"
  download_path="${output_path}.part"

  if [[ ! -f "$output_path" ]] || [[ "$(md5sum "$output_path" | awk '{print $1}')" != "$expected_md5" ]]; then
    curl -fL --retry 4 --retry-delay 2 "$url" -o "$download_path"
    actual_md5="$(md5sum "$download_path" | awk '{print $1}')"
    if [[ "$actual_md5" != "$expected_md5" ]]; then
      echo "Checksum mismatch for $asset_id: expected $expected_md5, got $actual_md5" >&2
      exit 1
    fi
    mv "$download_path" "$output_path"
  fi

  printf '%s\t%s\t%s\t%s\n' \
    "$asset_id" "$(basename "$output_path")" "$expected_md5" "$url" >>"$manifest_tmp"
done

mv "$manifest_tmp" "$output_dir/polyhaven_manifest.tsv"
trap - EXIT
