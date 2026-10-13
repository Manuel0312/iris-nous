import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';

/// Android: TelecomManager answer/reject.
/// iOS: CallKit — Iris presenta una chiamata nativa rispondibile con SÌ/NO.
class CallControlService {
  static const _channel = MethodChannel('com.irisnous.mobile/call_control');

  bool get supported => !kIsWeb && (Platform.isAndroid || Platform.isIOS);

  Future<Map<String, dynamic>> capabilities() async {
    if (!supported) {
      return {
        'platform': 'other',
        'canAnswerReject': false,
        'hasPermission': false,
      };
    }
    try {
      final raw = await _channel.invokeMethod<dynamic>('capabilities');
      if (raw is Map) return raw.cast<String, dynamic>();
    } catch (_) {}
    if (Platform.isIOS) {
      return {
        'platform': 'ios',
        'canAnswerReject': true,
        'mode': 'callkit',
        'hasPermission': true,
      };
    }
    return {'platform': 'android', 'canAnswerReject': true, 'hasPermission': false};
  }

  Future<bool> ensurePermission() async {
    if (!supported) return false;
    if (Platform.isIOS) return true;
    final status = await Permission.phone.request();
    return status.isGranted || status.isLimited;
  }

  /// Mostra la schermata chiamata nativa (CallKit su iOS). No-op utile su Android.
  Future<Map<String, dynamic>> presentIncoming({String caller = 'Chiamata Iris'}) async {
    if (!supported || !Platform.isIOS) {
      return {'ok': true, 'action': 'skip_android_uses_cellular'};
    }
    try {
      final raw = await _channel.invokeMethod<dynamic>(
        'presentIncoming',
        {'caller': caller},
      );
      if (raw is Map) return raw.cast<String, dynamic>();
    } on PlatformException catch (e) {
      return {'ok': false, 'reason': e.code, 'detail': e.message};
    }
    return {'ok': false, 'reason': 'no_result'};
  }

  Future<Map<String, dynamic>> answer() async {
    if (!supported) {
      return {'ok': false, 'reason': 'unsupported'};
    }
    await ensurePermission();
    try {
      final raw = await _channel.invokeMethod<dynamic>('answer');
      if (raw is Map) return raw.cast<String, dynamic>();
    } on PlatformException catch (e) {
      return {'ok': false, 'reason': e.code, 'detail': e.message};
    }
    return {'ok': false, 'reason': 'no_result'};
  }

  Future<Map<String, dynamic>> reject() async {
    if (!supported) {
      return {'ok': false, 'reason': 'unsupported'};
    }
    await ensurePermission();
    try {
      final raw = await _channel.invokeMethod<dynamic>('reject');
      if (raw is Map) return raw.cast<String, dynamic>();
    } on PlatformException catch (e) {
      return {'ok': false, 'reason': e.code, 'detail': e.message};
    }
    return {'ok': false, 'reason': 'no_result'};
  }

  Future<Map<String, dynamic>> end() async {
    if (!supported || !Platform.isIOS) {
      return {'ok': true, 'action': 'skip'};
    }
    try {
      final raw = await _channel.invokeMethod<dynamic>('end');
      if (raw is Map) return raw.cast<String, dynamic>();
    } on PlatformException catch (e) {
      return {'ok': false, 'reason': e.code, 'detail': e.message};
    }
    return {'ok': false, 'reason': 'no_result'};
  }

  Future<Map<String, dynamic>> runAction(String action) async {
    if (action == 'os_answer_call' || action == 'answer_call') {
      return answer();
    }
    if (action == 'os_reject_call' || action == 'reject_call') {
      return reject();
    }
    if (action == 'os_present_call' || action == 'present_call') {
      return presentIncoming();
    }
    return {'ok': false, 'reason': 'unknown_action'};
  }
}
