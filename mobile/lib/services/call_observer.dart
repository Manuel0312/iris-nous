import 'dart:async';

import 'package:flutter/foundation.dart';
import 'dart:io' show Platform;
import 'package:flutter/services.dart';

import 'iris_api.dart';

/// Bridge verso CXCallObserver (iOS) / futuro TelephonyCallback (Android).
class CallObserverService {
  CallObserverService(this.api);

  final IrisApi api;
  static const _channel = MethodChannel('com.irisnous.mobile/call_observer');

  StreamSubscription? _sub;
  bool _wasRinging = false;
  bool _wasActive = false;
  bool _running = false;

  bool get supported {
    if (kIsWeb) return false;
    return Platform.isIOS; // Android: fase successiva
  }

  Future<void> start() async {
    if (!supported || _running) return;
    _running = true;
    _channel.setMethodCallHandler(_onNative);
    try {
      await _channel.invokeMethod('start');
    } on MissingPluginException {
      _running = false;
    } on PlatformException {
      _running = false;
    }
  }

  Future<void> stop() async {
    _running = false;
    _channel.setMethodCallHandler(null);
    try {
      await _channel.invokeMethod('stop');
    } catch (_) {}
  }

  Future<void> _onNative(MethodCall call) async {
    if (call.method != 'onCallState') return;
    final args = Map<String, dynamic>.from(call.arguments as Map? ?? {});
    final ringing = args['incomingRinging'] == true;
    final active = args['anyActive'] == true || args['connected'] == true;

    if (ringing && !_wasRinging) {
      try {
        await api.sendEvent('call_incoming', caller: 'iPhone');
      } catch (_) {}
    }
    if (_wasActive && !active && !ringing) {
      try {
        await api.sendEvent('call_ended');
      } catch (_) {}
    }
    _wasRinging = ringing;
    _wasActive = active;
  }
}
