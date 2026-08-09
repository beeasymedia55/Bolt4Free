#!/usr/bin/env bash
# apk-convert-termux.sh — all-in-one APK conversion pipeline for Termux (Android)
#   decompile -> patch -> rebuild -> zipalign -> sign -> install
#
# Usage:
#   bash apk-convert-termux.sh -i EverCrossPro.apk --jadx
#   bash apk-convert-termux.sh -i app.apk --frida
#   bash apk-convert-termux.sh -i app.apk --patch-dir ./smali_patches --install
#
# First-time setup:
#   pkg update && pkg install -y apktool aapt aapt2 zipalign apksigner \
#                                openjdk-17 keytool jadx android-tools
#   termux-setup-storage            # grants access to ~/storage/downloads
#
# Wireless install (Android 11+): Settings > Developer options > Wireless debugging
#   export ADB_PAIR="<phone-ip>:<pairing-port>"   # under "Pair device with pairing code"
#   export ADB_PAIR_CODE="123456"                 # code shown there (rotates every session)
#   export ADB_CONNECT="<phone-ip>:<port>"        # port at top of Wireless debugging page

set -euo pipefail

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
[[ -d "$PREFIX" ]] || echo "[!] not running inside Termux? PREFIX=$PREFIX"

INPUT_APK=""; OUTPUT_APK=""
KEYSTORE=""; KEYSTORE_PASS="android"; KEY_ALIAS="modkey"
DO_JADX=0; DO_FRIDA=0; DO_PATCH_DIR=""; DO_INSTALL=0
DO_DECOMPILE_ONLY=0; KEEP_WORK=0
WORKDIR="$HOME/apk_work"
FRIDA_GADGET="${FRIDA_GADGET:-$HOME/frida-gadget-android-arm64.so}"

usage() {
    cat <<EOF
Usage: $0 -i <input.apk> [options]

  -i <apk>          input APK (required; e.g. ~/storage/downloads/app.apk)
  -o <apk>          output APK  (default: <input>-mod.apk)
  -k <keystore>     use existing keystore (else auto-generate debug one)
  --kp <pass>       keystore password (default: android)
  --jadx            also dump readable Java sources with jadx
  --frida           inject frida-gadget (arm64 .so + smali loader)
  --patch-dir <dir> copy pre-built smali patches into the rebuilt tree
  --install         install result (su/pm > wireless adb > copy hint)
  --decompile-only  stop after decompile
  --keep-work       keep $WORKDIR (default: removed on success)
  -h, --help        show this help

Env: FRIDA_GADGET, ADB_PAIR, ADB_PAIR_CODE, ADB_CONNECT, JAVA_OPTS
EOF
    exit "${1:-0}"
}

[[ $# -eq 0 ]] && usage 1
while [[ $# -gt 0 ]]; do
    case "$1" in
        -i) INPUT_APK="$2"; shift 2 ;;
        -o) OUTPUT_APK="$2"; shift 2 ;;
        -k) KEYSTORE="$2"; shift 2 ;;
        --kp) KEYSTORE_PASS="$2"; shift 2 ;;
        --jadx) DO_JADX=1; shift ;;
        --frida) DO_FRIDA=1; shift ;;
        --patch-dir) DO_PATCH_DIR="$2"; shift 2 ;;
        --install) DO_INSTALL=1; shift ;;
        --decompile-only) DO_DECOMPILE_ONLY=1; shift ;;
        --keep-work) KEEP_WORK=1; shift ;;
        -h|--help) usage 0 ;;
        *) echo "[-] unknown option: $1" >&2; usage 1 ;;
    esac
done

[[ -z "$INPUT_APK" ]] && { echo "[-] missing -i <input.apk>" >&2; usage 1; }
[[ -f "$INPUT_APK" ]] || { echo "[-] input APK not found: $INPUT_APK" >&2; exit 1; }
OUTPUT_APK="${OUTPUT_APK:-${INPUT_APK%.apk}-mod.apk}"

log() { printf '[+] %s\n' "$*"; }
die() { printf '[-] %s\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "missing: $1 — pkg install $2"; }

check_deps() {
    need apktool apktool
    need java openjdk-17
    need keytool keytool
    need zipalign zipalign
    need apksigner apksigner
    (( DO_JADX ))    && need jadx jadx
    (( DO_INSTALL )) && need adb android-tools
    (( DO_FRIDA )) && [[ -f "$FRIDA_GADGET" ]] || \
        die "frida-gadget missing: $FRIDA_GADGET (download android-arm64 build, or set FRIDA_GADGET)"
    log "dependencies OK"
}

decompile() {
    rm -rf "$WORKDIR"; mkdir -p "$WORKDIR"
    log "decompiling $INPUT_APK"
    apktool d -f -o "$WORKDIR/app" "$INPUT_APK"
    log "smali tree: $WORKDIR/app/smali*"
}

apply_patches() {
    if [[ -n "$DO_PATCH_DIR" ]]; then
        [[ -d "$DO_PATCH_DIR" ]] || die "patch dir not found: $DO_PATCH_DIR"
        log "copying smali patches from $DO_PATCH_DIR"
        cp -rv "$DO_PATCH_DIR"/. "$WORKDIR/app/"
    fi
    if (( DO_FRIDA )); then
        log "injecting frida-gadget (sleep mode, listen tcp:27042)"
        mkdir -p "$WORKDIR/app/lib/arm64-v8a"
        cp "$FRIDA_GADGET" "$WORKDIR/app/lib/arm64-v8a/libfrida-gadget.so"
        cat > "$WORKDIR/app/smali/com/mod/Loader.smali" <<'SMALI'
.class public Lcom/mod/Loader;
.super Ljava/lang/Object;

.method public static start(Landroid/content/Context;)V
    .locals 1
    :try_start
        const-string v0, "frida-gadget"
        invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch
    :catch
    return-void
.end method
SMALI
        log "note: wire Lcom/mod/Loader;->start() into the app's Application.onCreate"
        log "      (grep android:name in the <application> tag of AndroidManifest.xml)"
    fi
}

rebuild() {
    log "rebuilding (aapt2 if present, else aapt)"
    apktool b "$WORKDIR/app" -o "$WORKDIR/unsigned.apk"
}

align() {
    log "zipalign -f 4"
    zipalign -f 4 "$WORKDIR/unsigned.apk" "$WORKDIR/aligned.apk"
}

ensure_keystore() {
    if [[ -z "$KEYSTORE" ]]; then
        KEYSTORE="$WORKDIR/debug.keystore"
        [[ -f "$KEYSTORE" ]] || {
            log "generating debug keystore"
            keytool -genkeypair -v -keystore "$KEYSTORE" -storepass "$KEYSTORE_PASS" \
                -alias "$KEY_ALIAS" -keypass "$KEYSTORE_PASS" \
                -keyalg RSA -keysize 2048 -validity 10000 \
                -dname "CN=APK Convert,O=Assessment,C=US"
        }
    fi
}

sign() {
    ensure_keystore
    log "signing (v1+v2)"
    apksigner sign --ks "$KEYSTORE" --ks-pass "pass:$KEYSTORE_PASS" \
        --key-pass "pass:$KEYSTORE_PASS" --ks-key-alias "$KEY_ALIAS" \
        --out "$OUTPUT_APK" "$WORKDIR/aligned.apk"
    apksigner verify --print-certs "$OUTPUT_APK" | head -4
    log "signed output: $OUTPUT_APK"
}

dump_sources() {
    log "dumping Java sources with jadx"
    jadx -d "$WORKDIR/sources" "$INPUT_APK"
    log "sources: $WORKDIR/sources"
}

install_app() {
    local apk="$OUTPUT_APK"
    # 1) root path
    if command -v su >/dev/null 2>&1 && su -c true 2>/dev/null; then
        log "installing via su + pm"
        su -c "pm install -r '$apk'" && return
    fi
    # 2) wireless adb (same device, Android 11+)
    if ! adb devices | grep -q 'device$'; then
        if [[ -n "${ADB_CONNECT:-}" ]]; then
            if [[ -n "${ADB_PAIR:-}" ]]; then
                log "pairing with ${ADB_PAIR} ..."
                adb pair "$ADB_PAIR" "${ADB_PAIR_CODE:?set ADB_PAIR_CODE}"
            fi
            log "connecting ${ADB_CONNECT}"
            adb connect "$ADB_CONNECT"
        else
            die "no adb device. Set ADB_PAIR/ADB_PAIR_CODE/ADB_CONNECT, or copy the APK to" \
                "~/storage/downloads and install via a file manager"
        fi
    fi
    adb install -r "$apk"
}

main() {
    check_deps
    decompile
    (( DO_JADX )) && dump_sources
    (( DO_DECOMPILE_ONLY )) && { log "decompile-only: $WORKDIR/app"; exit 0; }
    apply_patches
    rebuild
    align
    sign
    (( DO_INSTALL )) && install_app
    (( KEEP_WORK )) || { rm -rf "$WORKDIR"; log "cleaned $WORKDIR"; }
    log "done -> $OUTPUT_APK"
}
main "$@"
