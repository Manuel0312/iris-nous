import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import 'auth_store.dart';

class IrisApiException implements Exception {
  IrisApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

/// Client HTTP verso Iris (pairing, heartbeat, eventi companion).
class IrisApi {
  IrisApi(this.store, {http.Client? client}) : _client = client ?? http.Client();

  final AuthStore store;
  final http.Client _client;

  Future<Uri> _uri(String path) async {
    final base = await store.baseUrl();
    return Uri.parse('$base$path');
  }

  Future<Map<String, String>> _authHeaders({bool requireToken = true}) async {
    final headers = <String, String>{
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
    final token = await store.deviceToken();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
      headers['X-Iris-Device-Token'] = token;
    } else if (requireToken) {
      throw IrisApiException('Telefono non associato. Completa Accedi / Associa.');
    }
    return headers;
  }

  Future<Map<String, dynamic>> pair({
    required String username,
    required String password,
    required String code,
  }) async {
    final res = await _client.post(
      await _uri(IrisConfig.pairPath),
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'username': username.trim(),
        'password': password,
        'code': code.trim(),
      }),
    );
    final body = _decode(res);
    if (res.statusCode >= 400) {
      throw IrisApiException(_detail(body), statusCode: res.statusCode);
    }
    final token = (body['device_token'] as String?) ?? '';
    final user = (body['username'] as String?) ?? username.trim();
    if (token.isEmpty) {
      throw IrisApiException('Il server non ha restituito il token dispositivo.');
    }
    await store.savePairing(token: token, username: user);
    return body;
  }

  Future<Map<String, dynamic>> heartbeat() async {
    final res = await _client.post(
      await _uri(IrisConfig.heartbeatPath),
      headers: await _authHeaders(),
    );
    final body = _decode(res);
    if (res.statusCode >= 400) {
      throw IrisApiException(_detail(body), statusCode: res.statusCode);
    }
    return body;
  }

  Future<Map<String, dynamic>> status() async {
    final res = await _client.get(
      await _uri(IrisConfig.statusPath),
      headers: await _authHeaders(requireToken: false),
    );
    final body = _decode(res);
    if (res.statusCode >= 400) {
      throw IrisApiException(_detail(body), statusCode: res.statusCode);
    }
    return body;
  }

  Future<Map<String, dynamic>> sendEvent(
    String event, {
    String caller = '',
    String track = '',
  }) async {
    final res = await _client.post(
      await _uri(IrisConfig.eventPath),
      headers: await _authHeaders(),
      body: jsonEncode({
        'event': event,
        'caller': caller,
        'track': track,
      }),
    );
    final body = _decode(res);
    if (res.statusCode >= 400) {
      throw IrisApiException(_detail(body), statusCode: res.statusCode);
    }
    return body;
  }

  Future<Map<String, dynamic>> musicNext() async {
    final res = await _client.post(
      await _uri(IrisConfig.musicNextPath),
      headers: await _authHeaders(),
    );
    final body = _decode(res);
    if (res.statusCode >= 400) {
      throw IrisApiException(_detail(body), statusCode: res.statusCode);
    }
    return body;
  }

  Map<String, dynamic> _decode(http.Response res) {
    if (res.body.isEmpty) return <String, dynamic>{};
    final decoded = jsonDecode(res.body);
    if (decoded is Map<String, dynamic>) return decoded;
    return <String, dynamic>{'raw': decoded};
  }

  String _detail(Map<String, dynamic> body) {
    final d = body['detail'];
    if (d is String) return d;
    if (d is List) return d.map((e) => e.toString()).join(' ');
    return body['message']?.toString() ?? 'Errore di rete Iris';
  }
}
