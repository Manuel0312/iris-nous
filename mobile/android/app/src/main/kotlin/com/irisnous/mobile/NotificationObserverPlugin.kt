package com.irisnous.mobile

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.text.TextUtils
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

class NotificationObserverPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {
    private lateinit var channel: MethodChannel
    private var appContext: Context? = null

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        appContext = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, CHANNEL)
        channel.setMethodCallHandler(this)
        instance = this
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
        if (instance === this) instance = null
        appContext = null
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        val ctx = appContext
        when (call.method) {
            "isEnabled" -> result.success(ctx != null && isNotificationAccessEnabled(ctx))
            "openSettings" -> {
                if (ctx == null) {
                    result.success(false)
                    return
                }
                try {
                    val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    ctx.startActivity(intent)
                    result.success(true)
                } catch (_: Exception) {
                    result.success(false)
                }
            }
            "start" -> {
                // Il servizio di sistema parte quando l'utente abilita l'accesso.
                // Teniamo vivo anche il foreground call watch.
                ctx?.let {
                    try {
                        IrisCallWatchService.start(it)
                    } catch (_: Exception) {
                    }
                }
                result.success(ctx != null && isNotificationAccessEnabled(ctx))
            }
            "stop" -> result.success(true)
            else -> result.notImplemented()
        }
    }

    private fun emitToFlutter(payload: Map<String, Any>) {
        channel.invokeMethod("onNotification", payload)
    }

    companion object {
        const val CHANNEL = "com.irisnous.mobile/notification_observer"
        @Volatile
        private var instance: NotificationObserverPlugin? = null

        fun emit(payload: Map<String, Any>) {
            instance?.emitToFlutter(payload)
        }

        fun isNotificationAccessEnabled(context: Context): Boolean {
            val cn = ComponentName(context, IrisNotificationListener::class.java)
            val flat = Settings.Secure.getString(
                context.contentResolver,
                "enabled_notification_listeners",
            ) ?: return false
            if (TextUtils.isEmpty(flat)) return false
            for (name in flat.split(":")) {
                val parsed = ComponentName.unflattenFromString(name) ?: continue
                if (parsed == cn) return true
            }
            // Android 13+ some OEMs flatten differently — also match package.
            return flat.contains(context.packageName)
        }
    }
}
