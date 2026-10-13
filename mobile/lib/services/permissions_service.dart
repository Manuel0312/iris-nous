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
            'Per rilevare lo squillo e aggiornare Iris. Poi SÌ/NO (cuffia virtuale) rispondono o rifiutano nel contesto Iris.',
        permission: Permission.phone,
        androidOnly: true,
        note:
            'Android: READ_PHONE_STATE. Iris non preme i tasti nativi della radio cellulare; SÌ/NO aggiornano In ascolto / coda telefono.',
      ),
      const IrisPermissionItem(
        id: 'notification',
        title: 'Notifiche',
        why:
            'Obbligatorie per tenere attivo «Iris in ascolto» in background (chiamate anche con schermo spento).',
        permission: Permission.notification,
        note: 'Android 13+: POST_NOTIFICATIONS. iOS: permesso notifiche.',
      ),
      const IrisPermissionItem(
        id: 'camera',
        title: 'Fotocamera',
        why: 'Per inquadrare il QR di Associazione da Ecosistema.',
        permission: Permission.camera,
        note: 'Solo lettura QR; nessuna foto inviata a Iris senza tua azione.',
      ),
      const IrisPermissionItem(
        id: 'ignore_battery',
        title: 'Esecuzione in background (batteria)',
        why:
            'Consigliato: altrimenti Android può sospendere il ponte chiamate con lo schermo spento.',
        permission: Permission.ignoreBatteryOptimizations,
        androidOnly: true,
        note: 'Collegato al servizio foreground IrisCallWatchService.',
      ),
      const IrisPermissionItem(
        id: 'ios_callkit',
        title: 'Osservazione chiamate (iOS)',
        why:
            'CXCallObserver rileva squillo / fine chiamata e lo manda a Iris. SÌ/NO nell’app simulano la cuffia sul contesto.',
        permission: null,
        iosOnly: true,
        note:
            'iOS non permette alle app di rispondere/rifiutare la tipica chiamata cellulare. Iris aggiorna il contesto demo.',
      ),
      const IrisPermissionItem(
        id: 'sms',
        title: 'SMS / messaggi',
        why: 'In futuro per notifiche messaggio — oggi puoi simulare il messaggio dall’app.',
        permission: null,
        planned: true,
        note: 'Non richiesto ora.',
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
