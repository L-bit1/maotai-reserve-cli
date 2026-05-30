package com.maotai.reserve.data

import com.google.gson.annotations.SerializedName

data class ApiEnvelope<T>(
    val code: Int,
    val message: String,
    val data: T?,
)

data class LoginRequest(val username: String, val password: String)

data class LoginData(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("expires_in") val expiresIn: Long,
)

data class MeData(val username: String)

data class AccountItem(
    val id: Int,
    val mobile: String,
    @SerializedName("mobile_raw") val mobileRaw: String?,
    val province: String?,
    val city: String?,
    val lat: String?,
    val lng: String?,
    @SerializedName("receiver_name") val receiverName: String?,
    @SerializedName("receiver_mobile") val receiverMobile: String?,
    val district: String?,
    @SerializedName("detail_address") val detailAddress: String?,
    @SerializedName("shop_strategy") val shopStrategy: String?,
    @SerializedName("shop_id") val shopId: String?,
    @SerializedName("egress_group") val egressGroup: String?,
    val enabled: Boolean,
    @SerializedName("has_token") val hasToken: Boolean,
    val remark: String?,
)

data class AccountListData(val total: Int, val items: List<AccountItem>)

data class AccountCreateBody(
    val mobile: String,
    val province: String = "",
    val city: String = "",
    val lat: String = "28.23",
    val lng: String = "112.94",
    @SerializedName("receiver_name") val receiverName: String = "",
    @SerializedName("receiver_mobile") val receiverMobile: String = "",
    val district: String = "",
    @SerializedName("detail_address") val detailAddress: String = "",
    @SerializedName("shop_strategy") val shopStrategy: String = "max_inventory",
    @SerializedName("shop_id") val shopId: String = "",
    @SerializedName("egress_group") val egressGroup: String = "",
    val enabled: Boolean = true,
)

data class AccountUpdateBody(
    val province: String? = null,
    val city: String? = null,
    val lat: String? = null,
    val lng: String? = null,
    @SerializedName("receiver_name") val receiverName: String? = null,
    @SerializedName("receiver_mobile") val receiverMobile: String? = null,
    val district: String? = null,
    @SerializedName("detail_address") val detailAddress: String? = null,
    @SerializedName("shop_strategy") val shopStrategy: String? = null,
    @SerializedName("shop_id") val shopId: String? = null,
    @SerializedName("egress_group") val egressGroup: String? = null,
    val enabled: Boolean? = null,
)

data class VcodeLoginBody(val vcode: String)

data class MessageData(val message: String)

data class SchedulerData(
    val enabled: Boolean,
    val running: Boolean,
    val jobs: List<SchedulerJob> = emptyList(),
)

data class SchedulerJob(
    val id: String,
    @SerializedName("next_run") val nextRun: String?,
)

data class DashboardData(
    @SerializedName("accounts_total") val accountsTotal: Int,
    @SerializedName("accounts_logged_in") val accountsLoggedIn: Int,
    @SerializedName("accounts_enabled") val accountsEnabled: Int,
    @SerializedName("products_enabled") val productsEnabled: Int,
    val scheduler: SchedulerData? = null,
    @SerializedName("last_job") val lastJob: LastJob?,
)

data class LastJob(
    val id: Int,
    val name: String,
    val status: String,
    val progress: Int,
)

data class QuickJobBody(
    val name: String = "每日自动预约",
    @SerializedName("dry_run") val dryRun: Boolean = false,
    @SerializedName("wait_until_reserve") val waitUntilReserve: Boolean = false,
)

data class QuickJobData(
    @SerializedName("job_id") val jobId: Int,
    val message: String,
)

data class JobItem(
    val id: Int,
    val name: String,
    val status: String,
    @SerializedName("dry_run") val dryRun: Boolean,
    val progress: Int,
    @SerializedName("log_preview") val logPreview: String?,
)

data class JobDetailData(
    val id: Int,
    val name: String,
    val status: String,
    val progress: Int,
    @SerializedName("log_text") val logText: String?,
)

data class LotteryItem(
    val id: Int,
    val mobile: String?,
    @SerializedName("item_name") val itemName: String?,
    @SerializedName("session_name") val sessionName: String?,
    val status: String?,
    @SerializedName("payment_status") val paymentStatus: String?,
    @SerializedName("order_id") val orderId: String?,
)

data class LotteryListData(val total: Int, val items: List<LotteryItem>)

data class SyncData(val synced: Int, val errors: List<String>?)

data class PendingListData(val total: Int, val items: List<LotteryItem>, val notice: String?)

data class UpdateCheckData(
    @SerializedName("has_update") val hasUpdate: Boolean,
    @SerializedName("version_code") val versionCode: Int,
    @SerializedName("version_name") val versionName: String,
    @SerializedName("download_url") val downloadUrl: String,
    @SerializedName("release_notes") val releaseNotes: String,
    @SerializedName("force_update") val forceUpdate: Boolean,
)
