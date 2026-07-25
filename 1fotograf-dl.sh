#!/bin/bash

# ============================================================
# fotograf.de / GotPhoto – Rev. 2
# Target: merletronnierfotografie.fotograf.de
# Code:   BL3G73V5
# ============================================================

BASE="https://merletronnierfotografie.fotograf.de"
CODE="BL3G73V5"
ALBUM="159779470"
CDN="https://img3c.fotocdn.de/kthfkr6w"
COOKIE=$(mktemp /tmp/fotograf_cookies_XXXXXX.txt)
OUTDIR="./fotograf_downloads_v2"
mkdir -p "$OUTDIR"

echo "============================================"
echo " fotograf.de Pentest v2"
echo " Code: $CODE | Album: $ALBUM"
echo "============================================"
echo ""

# ===== 1. SESSION-COOKIES HOLEN =====
echo "[1] Cookie-Consent setzen + Session init"
curl -s -c "$COOKIE" -b "$COOKIE" \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
  "$BASE/kunden/login" \
  -o /dev/null
echo "    Cookie-File: $COOKIE"
wc -c < "$COOKIE" | xargs echo "    Bytes:"

echo ""

# ===== 2. LOGIN-VERSUCH – ALLE VARIANTEN =====
echo "[2] Login-Test mit Access Code"

# Zuerst die echten Input-Namen aus der Seite extrahieren
echo "    -> Extrahiere Formularfelder aus Login-Seite..."
FORM_HTML=$(curl -s -b "$COOKIE" -c "$COOKIE" \
  -H "User-Agent: Mozilla/5.0" \
  "$BASE/kunden/login?access_code=$CODE")

# Suche nach input-Feldern
echo "$FORM_HTML" | grep -oP '<input[^>]*name="[^"]*"[^>]*>' 2>/dev/null | head -20
echo "$FORM_HTML" | grep -oP '<form[^>]*action="[^"]*"[^>]*>' 2>/dev/null | head -5

# CSRF-Token finden
CSRF_TOKEN=$(echo "$FORM_HTML" | grep -oP 'name="_token"[^>]*value="\K[^"]*' 2>/dev/null)
if [ -n "$CSRF_TOKEN" ]; then
  echo "    Gefunden: CSRF _token = ${CSRF_TOKEN:0:30}..."
fi

echo ""

# Mehrere POST-Varianten testen
for PARAM in "access_code" "accesscode" "code" "password" "_access_code" "accessCode"; do
  echo "   -> POST: $PARAM=$CODE"
  
  RESP=$(curl -s -c "$COOKIE" -b "$COOKIE" \
    -X POST "$BASE/kunden/login" \
    -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -H "X-Requested-With: XMLHttpRequest" \
    -d "$PARAM=$CODE" \
    -w "%{http_code} | %{url_effective} | %{redirect_url}" \
    -o "$OUTDIR/login_$PARAM.html" 2>/dev/null)
  
  HTTP=$(echo "$RESP" | awk '{print $1}')
  FINAL=$(echo "$RESP" | awk '{print $3}')
  REDIR=$(echo "$RESP" | awk '{print $5}')
  
  echo "      HTTP $HTTP | Final: $FINAL | Redirect: $REDIR"
  
  # Prüfe ob wir weitergeleitet wurden (weg von /login)
  FINAL_CLEAN=$(echo "$FINAL" | sed 's/|//g')
  if ! echo "$FINAL_CLEAN" | grep -qi "login"; then
    echo "   [!!!] Login erfolgreich mit PARAM=$PARAM! Redirect zu $FINAL_CLEAN"
    break
  fi
done

# ===== 3. AJAX-LOGIN VERSUCHEN =====
echo ""
echo "[3] AJAX-Login-Endpunkte testen"
for EP in "ajax/login" "api/login" "login/validate" "login/auth" "session/login" "api/v1/login" "rest/login"; do
  AJAX_RESP=$(curl -s -c "$COOKIE" -b "$COOKIE" \
    -X POST "$BASE/$EP" \
    -H "Content-Type: application/json" \
    -H "X-Requested-With: XMLHttpRequest" \
    -H "Accept: application/json" \
    -d "{\"access_code\":\"$CODE\",\"code\":\"$CODE\"}" \
    -o "$OUTDIR/ajax_$(echo $EP | tr '/' '_').json" \
    -w "%{http_code}" 2>/dev/null)
  
  if [ "$AJAX_RESP" != "404" ] && [ "$AJAX_RESP" != "500" ]; then
    echo "   [!] $EP -> HTTP $AJAX_RESP"
    head -10 "$OUTDIR/ajax_$(echo $EP | tr '/' '_').json"
  fi
done

# ===== 4. SESSION-TEST =====
echo ""
echo "[4] Session-Test (nach Login-Versuch)"
echo "    Cookies:"
cat "$COOKIE"

for URL in "$BASE/album/$ALBUM/" "$BASE/proofing/de-de/$ALBUM/packages/" "$BASE/albums/customer"; do
  HTTP=$(curl -s -c "$COOKIE" -b "$COOKIE" \
    -o "$OUTDIR/$(echo $URL | md5sum | cut -c1-8).html" \
    -w "%{http_code}" "$URL" 2>/dev/null)
  echo "    $URL -> HTTP $HTTP"
done

echo ""
echo "============================================"
echo " Fertig. Ergebnisse in: $OUTDIR/"
echo "============================================"
