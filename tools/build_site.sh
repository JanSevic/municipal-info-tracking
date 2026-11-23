#!/usr/bin/env bash
# Sestaví statický web do _site: web/ + konfigurace + data (z větve `data`).
#   tools/build_site.sh <adresar_s_daty> [vystup]
set -euo pipefail
DATA="${1:?adresář s daty}"
OUT="${2:-_site}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$OUT"; mkdir -p "$OUT/config" "$OUT/data"
cp -r "$ROOT"/web/* "$OUT/"
cp "$ROOT"/config/{obce.json,presets.json,public_key.pem} "$OUT/config/"
printf '{"repo": "%s", "branch": "%s"}\n' "${GITHUB_REPOSITORY:-}" "${SITE_BRANCH:-main}" > "$OUT/config/site.json"
if [ -f "$DATA/meta.json" ]; then
  cp -r "$DATA"/meta.json "$DATA"/records "$DATA"/fulltext "$OUT/data/"
else
  echo "Upozornění: zatím žádná data, web se sestaví prázdný." >&2
fi
touch "$OUT/.nojekyll"
echo "Web sestaven do $OUT"
