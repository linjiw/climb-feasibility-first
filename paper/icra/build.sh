#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
BUILD_DIR="$SCRIPT_DIR/build"
CACHE_DIR="${XDG_CACHE_HOME:-/tmp}/climb-icra"
export SOURCE_DATE_EPOCH=1788470400

IEEECONF_URL="https://ras.papercept.net/conferences/support/files/ieeeconf.zip"
IEEECONF_ZIP_SHA256="11d1051d5fe3dafd1e25bc7a8b66265cbe65dc135e26440cc6661baeeeb90c76"
IEEECONF_CLASS_SHA256="4befef671c2a996889d325f5170d3387bf42aac9a37dcaa93724ad49816e4ec2"
TECTONIC_URL="https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.17.0/tectonic-0.17.0-x86_64-unknown-linux-musl.tar.gz"
TECTONIC_SHA256="8533d07f9ccbd7a65824b9e0459041bca34af1eb33daba48f59215593753a3b7"

mkdir -p "$BUILD_DIR" "$CACHE_DIR"

verify_sha256() {
  local expected=$1
  local path=$2
  printf '%s  %s\n' "$expected" "$path" | sha256sum --check --status
}

if [[ ! -f "$CACHE_DIR/ieeeconf.cls" ]] || ! verify_sha256 "$IEEECONF_CLASS_SHA256" "$CACHE_DIR/ieeeconf.cls"; then
  archive=$(mktemp "$CACHE_DIR/ieeeconf.XXXXXX.zip")
  curl -fsSL "$IEEECONF_URL" -o "$archive"
  verify_sha256 "$IEEECONF_ZIP_SHA256" "$archive"
  unzip -p "$archive" ieeeconf.cls > "$CACHE_DIR/ieeeconf.cls.tmp"
  verify_sha256 "$IEEECONF_CLASS_SHA256" "$CACHE_DIR/ieeeconf.cls.tmp"
  mv "$CACHE_DIR/ieeeconf.cls.tmp" "$CACHE_DIR/ieeeconf.cls"
  rm "$archive"
fi

if [[ ! -x "$CACHE_DIR/tectonic" ]]; then
  archive=$(mktemp "$CACHE_DIR/tectonic.XXXXXX.tar.gz")
  curl -fsSL "$TECTONIC_URL" -o "$archive"
  verify_sha256 "$TECTONIC_SHA256" "$archive"
  tar -xzf "$archive" -C "$CACHE_DIR" tectonic
  chmod +x "$CACHE_DIR/tectonic"
  rm "$archive"
fi

cp "$CACHE_DIR/ieeeconf.cls" "$BUILD_DIR/ieeeconf.cls"
cp "$SCRIPT_DIR/root.tex" "$SCRIPT_DIR/references.bib" "$BUILD_DIR/"
cp "$REPO_ROOT/paper/figures/f1_feasibility_first.pdf" \
  "$REPO_ROOT/paper/figures/f2_bank_scale.pdf" "$BUILD_DIR/"

(
  cd "$BUILD_DIR"
  "$CACHE_DIR/tectonic" --chatter minimal --keep-logs --keep-intermediates root.tex
)

PDF_PATH="$BUILD_DIR/root.pdf"
PDF_INFO=$(pdfinfo "$PDF_PATH")
printf '%s\n' "$PDF_INFO" | grep -E '^(Pages|Page size):'
FONT_INFO=$(pdffonts "$PDF_PATH")
printf '%s\n' "$FONT_INFO"

PAGES=$(printf '%s\n' "$PDF_INFO" | awk '/^Pages:/ {print $2}')
if (( PAGES > 8 )); then
  echo "error: ICRA submission exceeds the eight-page total limit" >&2
  exit 1
fi
if ! printf '%s\n' "$PDF_INFO" | grep -q '^Page size:.*(letter)$'; then
  echo "error: ICRA submission is not US Letter" >&2
  exit 1
fi
if printf '%s\n' "$FONT_INFO" | grep -q 'Type 3'; then
  echo "error: PDF contains a disallowed Type 3 font" >&2
  exit 1
fi
if ! printf '%s\n' "$FONT_INFO" | awk 'NR > 2 && $(NF-4) != "yes" {exit 1}'; then
  echo "error: PDF contains an unembedded font" >&2
  exit 1
fi
if grep -Eq 'Overfull \\hbox|Citation .* undefined|undefined references' "$BUILD_DIR/root.log"; then
  echo "error: LaTeX log contains an overfull box or unresolved citation" >&2
  exit 1
fi

cp "$PDF_PATH" "$SCRIPT_DIR/ICRA_DRAFT.pdf"
