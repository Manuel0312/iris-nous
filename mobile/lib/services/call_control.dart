import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';

/// Android: TelecomManager answer/reject. iOS: not supported by the OS.
class CallControlService {
  static const _channel = MethodChannel('com.irisnous.mobile/call_control');

  bool get supported => !kIsWeb && Platform.isAndroid;

  Future<Map<String, dynamic>> capabilities() async {
    if (!supported) {
      return {
        'platform': Platform.isIOS ? 'ios' : 'other',
        'canAnswerReject': false,
        'hasPermission': false,
      };
    }
    try {
      final raw = await _channel.invokeMethod<dynamic>('capabilities');
      if (raw is Map) return raw.cast<String, dynamic>();
    } catch (_) {}
    return {'platform': 'android', 'canAnswerReject': true, 'hasPermission': false};
  }

  Future<bool> ensurePermission() async {
    if (!supported) return false;
    // permission_handler maps phone group; ANSWER_PHONE_CALLS is requested with phone on modern Android.
    final status = await Permission.phone.request();
    return status.isGranted || status.isLimited;
  }

  Future<Map<String, dynamic>> answer() async {
    if (!supported) {
      return {'ok': false, 'reason': 'ios_unsupported'};
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
      return {'ok': false, 'reason': 'ios_unsupported'};
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

  Future<Map<String, dynamic>> runAction(String action) async {
    if (action == 'os_answer_call' || action == 'answer_call') {
      return answer();
    }
    if (action == 'os_reject_call' || action == 'reject_call') {
      return reject();
    }
    return {'ok': false, 'reason': 'unknown_action'};
  }
}
