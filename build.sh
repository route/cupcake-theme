#!/usr/bin/env bash
# Packages src/ into a plugin zip that JetBrains IDEs accept via
# Settings -> Plugins -> gear -> Install Plugin from Disk...
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
name="cupcake"
version="$(sed -n 's/.*<version>\(.*\)<\/version>.*/\1/p' "$root/src/META-INF/plugin.xml")"
stage="$root/build/$name/lib"

rm -rf "$root/build"
mkdir -p "$stage"
(cd "$root/src" && jar --create --file "$stage/$name-$version.jar" .)
rm -f "$root/dist/$name-$version.zip"
(cd "$root/build" && zip -qr "$root/dist/$name-$version.zip" "$name")
rm -rf "$root/build"

echo "dist/$name-$version.zip"
