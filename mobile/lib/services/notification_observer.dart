import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import 'iris_api.dart';

/// Android: NotificationListener → Iris (WhatsApp / Telegram / SMS).
/// iOS: non supportato (limite sistema).
class NotificationObserverService {
  NotificationObserverService(this.api, {this.onMessage});

  final IrisApi api;
  final Future<void> Function(Map<String, dynamic> payload)? onMessage;

  static const _channel = MethodChannel('com.irisnous.mobile/notification_observer');

  bool _running = false;
  bool enabled = false;
  String? lastError;
  String? lastSent;
  VoidCallback? onChanged;

  bool get supported {
    if (kIsWeb) return false;
    return Platform.isAndroid;
  }

  Future<bool> refreshEnabled() async {
    if (!supported) {
      enabled = false;
      return false;
    }
    try {
      final ok = await _channel.invokeMethod<bool>('isEnabled');
      enabled = ok == true;
    } catch (_) {
      enabled = false;
    }
    onChanged?.call();
    return enabled;
  }

  Future<void> openSettings() async {
    if (!supported) return;
    try {
      await _channel.invokeMethod('openSettings');
    } catch (_) {}
  }

  Future<void> start() async {
    if (!supported) return;
    await stop();
    _running = true;
    lastError = null;
    _channel.setMethodCallHandler(_onNative);
    try {
      final ok = await _channel.invokeMethod<bool>('start');
      enabled = ok == true;
      if (!enabled) {
        lastError =
            'Attiva «Accesso alle notifiche» per Iris Nous (Permessi → Messaggi).';
      }
    } on MissingPluginException {
      _running = false;
      lastError = 'Plugin notifiche assente';
    } on PlatformException catch (e) {
      _running = false;
      lastError = e.message ?? 'Errore plugin notifiche';
    }
    onChanged?.call();
  }

  Future<void> stop() async {
    _running = false;
    _channel.setMethodCallHandler(null);
    try {
      await _channel.invokeMethod('stop');
    } catch (_) {}
  }

  Future<void> _onNative(MethodCall call) async {
    if (!_running || call.method != 'onNotification') return;
    final args = Map<String, dynamic>.from(call.arguments as Map? ?? {});
    final sender = (args['sender'] ?? 'Messaggio').toString();
    final preview = (args['preview'] ?? '').toString();
    final app = (args['app'] ?? 'WhatsApp').toString();
    try {
      await api.sendEvent(
        'notification_message',
        caller: sender,
        sender: sender,
        preview: preview,
        app: app,
      );
      lastSent = 'messaggio $app → Iris';
      lastError = null;
      try {
        await onMessage?.call(args);
      } catch (_) {}
    } catch (e) {
      lastError = 'Invio messaggio fallito: $e';
    }
    onChanged?.call();
  }
}
