import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config.dart';

/// Persistenza pairing: token dispositivo + URL base.
class AuthStore {
  AuthStore({
    FlutterSecureStorage? secure,
  }) : _secure = secure ?? const FlutterSecureStorage();

  static const _kToken = 'iris_device_token';
  static const _kUsername = 'iris_username';
  static const _kBaseUrl = 'iris_base_url';

  final FlutterSecureStorage _secure;

  Future<String> baseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kBaseUrl) ?? IrisConfig.defaultBaseUrl;
  }

  Future<void> setBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    final cleaned = url.trim().replaceAll(RegExp(r'/$'), '');
    await prefs.setString(_kBaseUrl, cleaned.isEmpty ? IrisConfig.defaultBaseUrl : cleaned);
  }

  Future<String?> deviceToken() => _secure.read(key: _kToken);

  Future<String?> username() => _secure.read(key: _kUsername);

  Future<bool> isPaired() async {
    final t = await deviceToken();
    return t != null && t.isNotEmpty;
  }

  Future<void> savePairing({
    required String token,
    required String username,
  }) async {
    await _secure.write(key: _kToken, value: token);
    await _secure.write(key: _kUsername, value: username);
  }

  Future<void> clear() async {
    await _secure.delete(key: _kToken);
    await _secure.delete(key: _kUsername);
  }
}
