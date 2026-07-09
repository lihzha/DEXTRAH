#!/usr/bin/env bash
set -euo pipefail

output_dir="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
user_agent="${POLYHAVEN_USER_AGENT:-DEXTRAH-YAM-Research/1.0}"
mkdir -p "$output_dir"

asset_ids=(
  anti_skid_tiles
  anti_slip_concrete
  brown_floor_tiles
  checkered_pavement_tiles
  concrete_floor
  concrete_floor_02
  concrete_floor_painted
  concrete_floor_worn_001
  dirty_carpet
  dirty_tiles
  floor_tiles_02
  floor_tiles_06
  garage_floor
  grey_cartago_01
  hangar_concrete_floor
  interior_tiles
  marble_01
  metal_plate
  painted_concrete
  running_track
  scuffed_cement
  smooth_concrete_floor
  tiled_floor_001
  worn_tile_floor
)

manifest_tmp="$(mktemp)"
trap 'rm -f "$manifest_tmp"' EXIT
printf 'asset_id\tfile\tmd5\turl\n' >"$manifest_tmp"

for asset_id in "${asset_ids[@]}"; do
  files_json="$(curl -A "$user_agent" -fsSL --retry 4 "https://api.polyhaven.com/files/${asset_id}")"
  url="$(jq -er '.Diffuse["1k"].jpg.url' <<<"$files_json")"
  expected_md5="$(jq -er '.Diffuse["1k"].jpg.md5' <<<"$files_json")"
  output_path="$output_dir/${asset_id}_diff_1k.jpg"
  download_path="${output_path}.part"

  if [[ ! -f "$output_path" ]] || [[ "$(md5sum "$output_path" | awk '{print $1}')" != "$expected_md5" ]]; then
    curl -A "$user_agent" -fL --retry 4 --retry-delay 2 "$url" -o "$download_path"
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
