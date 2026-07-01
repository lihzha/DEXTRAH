CC0 tabletop wood textures downloaded from Poly Haven for YAM policy scene randomization.

- `wood_table_001_diff_1k.jpg`: https://polyhaven.com/a/wood_table_001
- `plank_flooring_02_diff_1k.jpg`: https://polyhaven.com/a/plank_flooring_02
- `plank_flooring_02_diff_1k.png`: PNG conversion of `plank_flooring_02_diff_1k.jpg`
  for renderers that handle PNG texture inputs more reliably than JPG.

Run `download_selected_polyhaven_assets.sh` to fetch the additional curated
1K diffuse maps used by the final visual replay. The selection spans light,
medium, and dark natural wood, veneer, laminate, plywood, and clean plank/table
finishes while excluding bark, painted, mossy, and heavily weathered surfaces.
The script verifies every file against the MD5 checksum returned by Poly
Haven's API and writes `polyhaven_manifest.tsv` with source URLs and checksums.

These are 1K diffuse JPG maps. Poly Haven assets are CC0:
https://polyhaven.com/license
