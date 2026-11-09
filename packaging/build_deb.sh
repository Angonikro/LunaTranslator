#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
VERSION="$(python3 -c 'from runpy import run_path; print(run_path("'"$ROOT"'/version.py")["VERSION"])')"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PKG="$WORK/lunatranslator"
install -d "$PKG/usr/share/lunatranslator" "$PKG/usr/bin" \
    "$PKG/usr/share/applications" \
    "$PKG/usr/share/icons/hicolor/scalable/apps" "$PKG/DEBIAN"
cp -a "$ROOT/main.py" "$ROOT/version.py" "$ROOT/lunatranslator" "$PKG/usr/share/lunatranslator/"
install -m 644 "$ROOT/packaging/icons/lunatranslator.svg" \
    "$PKG/usr/share/icons/hicolor/scalable/apps/lunatranslator.svg"
cat > "$PKG/usr/bin/lunatranslator" <<'EOF'
#!/bin/sh
exec python3 /usr/share/lunatranslator/main.py "$@"
EOF
chmod 755 "$PKG/usr/bin/lunatranslator"
cat > "$PKG/usr/share/applications/lunatranslator.desktop" <<'EOF'
[Desktop Entry]
Name=LunaTranslator
GenericName=Übersetzer
Comment=Texte online übersetzen
Exec=lunatranslator
Icon=lunatranslator
Terminal=false
Type=Application
Categories=Utility;Education;Office;
StartupNotify=true
EOF
cp "$ROOT/packaging/debian/control" "$PKG/DEBIAN/control"
sed -i "s/^Version:.*/Version: $VERSION/" "$PKG/DEBIAN/control"
cat > "$PKG/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 755 "$PKG/DEBIAN" "$PKG/DEBIAN/postinst"
dpkg-deb --build --root-owner-group "$PKG" "$ROOT/lunatranslator_${VERSION}_all.deb"
