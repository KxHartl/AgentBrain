#!/usr/bin/env bash
# Compile each LaTeX template with Tectonic to catch engine/font/Croatian regressions.
# Renders the master via render_template.py (the same path latex_architect uses),
# compiles with Tectonic, and fails on a missing PDF or dropped Croatian glyphs.
#
# Usage: ./tests/compile-template.sh [format ...]   (default: all LaTeX formats)
set -u

BRAIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if (($# > 0)); then
  FORMATS=("$@")
else
  FORMATS=(fsb-seminar fsb-thesis fsb-paper fsb-presentation)
fi

if ! command -v tectonic >/dev/null 2>&1; then
  echo "ERROR: tectonic not found — required for the template compile test." >&2
  exit 1
fi

fail=0
for fmt in "${FORMATS[@]}"; do
  echo "=== $fmt ==="
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/.ai/config"
  cat > "$tmp/.ai/config/project.yaml" <<EOF
name: "Test Projekt"
latex_format: "$fmt"
author_name: "Ivan Horvat"
course_name: "TEST KOLEGIJ ČĆŽŠĐ"
seminar_title: "Naslov rada s hrvatskim slovima: žđšćč ŽĐŠĆČ"
seminar_title_short: "Kratki naslov žđšćč"
professor_title: "Prof. dr. sc."
professor_name: "Ana Marić"
include_lof: true
include_lot: true
EOF

  if ! python "$BRAIN_ROOT/scripts/render_template.py" \
        --project-root "$tmp" --format "$fmt" --scaffold --fill-stubs --force; then
    echo "  RENDER FAILED"; fail=1; rm -rf "$tmp"; continue
  fi

  mkdir -p "$tmp/docs/build"
  ( cd "$tmp" && tectonic -X compile docs/main.tex --outdir docs/build --keep-logs ) \
    >"$tmp/compile.out" 2>&1
  rc=$?
  log="$tmp/docs/build/main.log"

  if [[ $rc -ne 0 ]]; then
    echo "  COMPILE FAILED (rc=$rc)"; tail -25 "$tmp/compile.out"; fail=1
  elif [[ ! -f "$tmp/docs/build/main.pdf" ]]; then
    echo "  NO PDF produced"; tail -25 "$tmp/compile.out"; fail=1
  else
    # Count real glyph drops only. "Missing character ... in font nullfont" is a
    # benign Beamer artefact (a char typeset before any font is active) and does
    # NOT mean our font lacks a Croatian glyph, so it is excluded.
    miss=$(grep "Missing character" "$log" 2>/dev/null | grep -vc "nullfont" || true)
    miss=${miss:-0}
    if [[ "$miss" -gt 0 ]]; then
      echo "  FAIL: $miss 'Missing character' warnings (Croatian glyphs dropped):"
      grep "Missing character" "$log" | grep -v "nullfont" | head -3
      fail=1
    else
      echo "  OK: PDF built, no missing characters"
    fi
  fi
  rm -rf "$tmp"
done

if [[ $fail -ne 0 ]]; then
  echo "TEMPLATE COMPILE TEST: FAILED"
else
  echo "TEMPLATE COMPILE TEST: PASSED"
fi
exit $fail
