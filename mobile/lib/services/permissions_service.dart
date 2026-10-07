import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';

/// Descrizione IT di un permesso companion (richiesta graduale in UI).
class IrisPermissionItem {
  const IrisPermissionItem({
    required this.id,
    required this.title,
    required this.why,
    required this.permission,
    this.androidOnly = false,
    this.iosOnly = false,
    this.planned = false,
    this.note = '',
  });

  final String id;
  final String title;
  final String why;
  final Permission? permission;
  final bool androidOnly;
  final bool iosOnly;
  /// Non richiesto ora (es. SMS) — solo documentato.
  final bool planned;
  final String note;
}

class PermissionsService {
  /// Elenco mostrato in schermata Permessi (non tutti richiesti subito).
  List<IrisPermissionItem> catalog() {
    final items = <IrisPermissionItem>[
      const IrisPermissionItem(
        id: 'phone',
        title: 'Stato telefono / chiamate',
        why:
            'Per capire se arriva una chiamata cellulare e aggiornare Iris (In ascolto), senza rispondere al posto tuo.',
        permission: Permission.phone,
        androidOnly: true,
        note:
            'Android: READ_PHONE_STATE (+ su alcuni OEM READ_CALL_LOG). Da Android 12+ il numero chiamante può essere limitato. Non implementa risposta/rifiuto OS.',
      ),
      const IrisPermissionItem(
        id: 'notification',
        title: 'Notifiche',
        why:
            'Per avvisarti quando Iris riceve un evento (chiamata rilevata, heartbeat in background).',
        permission: Permission.notification,
        note: 'Android 13+: POST_NOTIFICATIONS. iOS: permesso notifiche al primo invio.',
      ),
      const IrisPermissionItem(
        id: 'ignore_battery',
        title: 'Esecuzione in background (batteria)',
        why:
            'Per tenere il heartbeat verso Iris anche con lo schermo spento (servizio in primo piano su Android).',
        permission: Permission.ignoreBatteryOptimizations,
        androidOnly: true,
        note: 'Collegato a FOREGROUND_SERVICE; non è obbligatorio al primo avvio.',
      ),
      const IrisPermissionItem(
        id: 'ios_callkit',
        title: 'Osservazione chiamate (iOS)',
        why:
            'Per rilevare squillo / connessa / terminata con CXCallObserver (CallKit) e dirlo a Iris.',
        permission: null,
        iosOnly: true,
        note:
            'Nessuna stringa privacy obbligatoria solo per osservare. Non può rispondere/rifiutare la tipica chiamata cellulare. VoIP CallKit provider = fase successiva.',
      ),
      const IrisPermissionItem(
        id: 'sms',
        title: 'SMS / messaggi',
        why: 'In futuro, solo se Iris leggerà notifiche messaggio — oggi non serve.',
        permission: null,
        planned: true,
        note: 'Non richiesto. Niente READ_SMS / accesso iMessage.',
      ),
    ];

    if (kIsWeb) return items;
    if (Platform.isAndroid) {
      return items.where((e) => !e.iosOnly).toList();
    }
    if (Platform.isIOS) {
      return items.where((e) => !e.androidOnly).toList();
    }
    return items;
  }

  Future<PermissionStatus> statusOf(IrisPermissionItem item) async {
    if (item.permission == null || item.planned) {
      return PermissionStatus.denied;
    }
    return item.permission!.status;
  }

  Future<PermissionStatus> request(IrisPermissionItem item) async {
    if (item.planned || item.permission == null) {
      return PermissionStatus.denied;
    }
    return item.permission!.request();
  }

  String labelFor(PermissionStatus s) {
    switch (s) {
      case PermissionStatus.granted:
      case PermissionStatus.limited:
        return 'Consentito';
      case PermissionStatus.denied:
        return 'Non ancora';
      case PermissionStatus.permanentlyDenied:
        return 'Bloccato — apri Impostazioni';
      case PermissionStatus.restricted:
        return 'Limitato dal sistema';
      case PermissionStatus.provisional:
        return 'Provvisorio';
    }
  }
}
