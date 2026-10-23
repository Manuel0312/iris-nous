package com.irisnous.mobile

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.app.Notification

/**
 * Legge anteprime notifiche (WhatsApp e simili) e le inoltra a Flutter.
 * Richiede il permesso di sistema "Accesso alle notifiche".
 */
class IrisNotificationListener : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        if (sbn == null || sbn.isOngoing) return
        val pkg = sbn.packageName ?: return
        if (pkg !in WATCHED) return
        if (pkg == applicationContext.packageName) return

        val extras = sbn.notification?.extras ?: return
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.trim().orEmpty()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()?.trim().orEmpty()
        val big = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()?.trim().orEmpty()
        val preview = when {
            big.isNotEmpty() -> big
            text.isNotEmpty() -> text
            else -> ""
        }
        if (title.isEmpty() && preview.isEmpty()) return

        val key = "$pkg|$title|$preview"
        val now = System.currentTimeMillis()
        synchronized(lock) {
            if (key == lastKey && now - lastAt < 2500L) return
            lastKey = key
            lastAt = now
        }

        val appLabel = when (pkg) {
            "com.whatsapp", "com.whatsapp.w4b" -> "WhatsApp"
            "org.telegram.messenger", "org.telegram.messenger.web" -> "Telegram"
            "com.google.android.apps.messaging" -> "Messaggi"
            else -> pkg.substringAfterLast('.').replaceFirstChar { it.uppercase() }
        }

        NotificationObserverPlugin.emit(
            mapOf(
                "package" to pkg,
                "app" to appLabel,
                "sender" to (if (title.isNotEmpty()) title else appLabel),
                "preview" to preview.take(500),
                "postedAt" to now,
            )
        )
    }

    companion object {
        private val lock = Any()
        private var lastKey: String = ""
        private var lastAt: Long = 0L

        private val WATCHED = setOf(
            "com.whatsapp",
            "com.whatsapp.w4b",
            "org.telegram.messenger",
            "org.telegram.messenger.web",
            "com.google.android.apps.messaging",
            "com.samsung.android.messaging",
        )
    }
}
