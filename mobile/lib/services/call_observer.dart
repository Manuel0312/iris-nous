import 'dart:async';

import 'package:flutter/foundation.dart';
import 'dart:io' show Platform;
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';

import 'iris_api.dart';

/// Bridge verso CXCallObserver (iOS) e TelephonyCallback (Android).
class CallObserverService {
  CallObserverService(this.api);

  final IrisApi api;
  static const _channel = MethodChannel('com.irisnous.mobile/call_observer');

  bool _wasRinging = false;
  bool _wasActive = false;
  bool _running = false;
  bool listening = false;
  bool permitted = true;
  String? lastError;
  String? lastSent;
  VoidCallback? onChanged;

  bool get supported {
    if (kIsWeb) return false;
    return Platform.isIOS || Platform.isAndroid;
  }

  String get _callerLabel {
    if (Platform.isAndroid) return 'Android';
    if (Platform.isIOS) return 'iPhone';
    return 'telefono';
  }

  Future<void> start() async {
    if (!supported) return;
    await stop();
    _running = true;
    lastError = null;
    _channel.setMethodCallHandler(_onNative);

    if (Platform.isAndroid) {
      final status = await Permission.phone.request();
      permitted = status.isGranted || status.isLimited;
      if (!permitted) {
        listening = false;
        lastError = 'Permesso stato telefono mancante';
        onChanged?.call();
        return;
      }
    }

    try {
      final ok = await _channel.invokeMethod<bool>('start');
      listening = ok == true;
      if (ok == false) {
        permitted = false;
        lastError = 'Listener nativo non avviato';
      }
    } on MissingPluginException {
      _running = false;
      listening = false;
      lastError = 'Plugin chiamate assente';
    } on PlatformException catch (e) {
      _running = false;
      listening = false;
      lastError = e.message ?? 'Errore plugin chiamate';
    }
    onChanged?.call();
  }

  Future<void> stop() async {
    _running = false;
    listening = false;
    _channel.setMethodCallHandler(null);
    try {
      await _channel.invokeMethod('stop');
    } catch (_) {}
  }

  Future<void> _onNative(MethodCall call) async {
    if (call.method != 'onCallState') return;
    final args = Map<String, dynamic>.from(call.arguments as Map? ?? {});
    if (args.containsKey('permitted')) {
      permitted = args['permitted'] != false;
    }
    final ringing = args['incomingRinging'] == true;
    final active = args['anyActive'] == true || args['connected'] == true;

    if (ringing && !_wasRinging) {
      try {
        await api.sendEvent('call_incoming', caller: _callerLabel);
        lastSent = 'call_incoming → Iris';
        lastError = null;
      } catch (e) {
        lastError = 'Invio squillo fallito: $e';
      }
      onChanged?.call();
    }
    if (_wasActive && !active && !ringing) {
      try {
        await api.sendEvent('call_ended');
        lastSent = 'call_ended → Iris';
        lastError = null;
      } catch (e) {
        lastError = 'Invio fine chiamata fallito: $e';
      }
      onChanged?.call();
    }
    _wasRinging = ringing;
    _wasActive = active;
  }
}
