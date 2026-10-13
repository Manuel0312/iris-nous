package com.irisnous.mobile

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.telecom.TelecomManager
import androidx.core.content.ContextCompat
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Best-effort OS answer / reject for cellular calls (Android).
 * Requires ANSWER_PHONE_CALLS. Deprecated TelecomManager APIs still work on many devices;
 * OEM policies may still block — then Iris keeps context-only behavior.
 */
class CallControlPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {
    private lateinit var channel: MethodChannel
    private var appContext: Context? = null

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        appContext = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, CHANNEL)
        channel.setMethodCallHandler(this)
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
        appContext = null
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "capabilities" -> result.success(
                mapOf(
                    "platform" to "android",
                    "canAnswerReject" to true,
                    "hasPermission" to hasAnswerPermission(),
                ),
            )
            "answer" -> result.success(runAnswer())
            "reject" -> result.success(runReject())
            else -> result.notImplemented()
        }
    }

    private fun hasAnswerPermission(): Boolean {
        val ctx = appContext ?: return false
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return false
        return ContextCompat.checkSelfPermission(ctx, Manifest.permission.ANSWER_PHONE_CALLS) ==
            PackageManager.PERMISSION_GRANTED
    }

    private fun telecom(): TelecomManager? {
        val ctx = appContext ?: return null
        return ctx.getSystemService(Context.TELECOM_SERVICE) as? TelecomManager
    }

    private fun runAnswer(): Map<String, Any?> {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return mapOf("ok" to false, "reason" to "android_too_old")
        }
        if (!hasAnswerPermission()) {
            return mapOf("ok" to false, "reason" to "missing_answer_permission")
        }
        val tm = telecom() ?: return mapOf("ok" to false, "reason" to "no_telecom")
        return try {
            @Suppress("DEPRECATION")
            tm.acceptRingingCall()
            mapOf("ok" to true, "action" to "answer")
        } catch (e: SecurityException) {
            mapOf("ok" to false, "reason" to "security", "detail" to (e.message ?: ""))
        } catch (e: Exception) {
            mapOf("ok" to false, "reason" to "error", "detail" to (e.message ?: ""))
        }
    }

    private fun runReject(): Map<String, Any?> {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) {
            return mapOf("ok" to false, "reason" to "android_too_old")
        }
        if (!hasAnswerPermission()) {
            return mapOf("ok" to false, "reason" to "missing_answer_permission")
        }
        val tm = telecom() ?: return mapOf("ok" to false, "reason" to "no_telecom")
        return try {
            @Suppress("DEPRECATION")
            val ended = tm.endCall()
            mapOf("ok" to ended, "action" to "reject", "reason" to if (ended) null else "endCall_false")
        } catch (e: SecurityException) {
            mapOf("ok" to false, "reason" to "security", "detail" to (e.message ?: ""))
        } catch (e: Exception) {
            mapOf("ok" to false, "reason" to "error", "detail" to (e.message ?: ""))
        }
    }

    companion object {
        const val CHANNEL = "com.irisnous.mobile/call_control"
    }
}
