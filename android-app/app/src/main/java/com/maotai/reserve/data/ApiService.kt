package com.maotai.reserve.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {
    @GET("app/check-update")
    suspend fun checkUpdate(@Query("version_code") versionCode: Int): ApiEnvelope<UpdateCheckData>

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): ApiEnvelope<LoginData>

    @GET("auth/me")
    suspend fun me(): ApiEnvelope<MeData>

    @GET("mobile/dashboard")
    suspend fun dashboard(): ApiEnvelope<DashboardData>

    @POST("mobile/quick-reserve")
    suspend fun quickReserve(@Body body: QuickJobBody): ApiEnvelope<QuickJobData>

    @GET("accounts")
    suspend fun accounts(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 100,
        @Query("search") search: String? = null,
    ): ApiEnvelope<AccountListData>

    @POST("accounts")
    suspend fun createAccount(@Body body: AccountCreateBody): ApiEnvelope<AccountItem>

    @PUT("accounts/{id}")
    suspend fun updateAccount(
        @Path("id") id: Int,
        @Body body: AccountUpdateBody,
    ): ApiEnvelope<AccountItem>

    @POST("accounts/{id}/send-vcode")
    suspend fun sendVcode(@Path("id") id: Int): ApiEnvelope<MessageData>

    @POST("accounts/{id}/login")
    suspend fun loginAccount(
        @Path("id") id: Int,
        @Body body: VcodeLoginBody,
    ): ApiEnvelope<Any?>

    @GET("jobs")
    suspend fun jobs(): ApiEnvelope<List<JobItem>>

    @GET("jobs/{id}")
    suspend fun jobDetail(@Path("id") id: Int): ApiEnvelope<JobDetailData>

    @POST("lottery/sync")
    suspend fun syncLottery(@Query("today_only") todayOnly: Boolean = true): ApiEnvelope<SyncData>

    @GET("lottery/results")
    suspend fun lotteryResults(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 100,
    ): ApiEnvelope<LotteryListData>

    @GET("payments/pending")
    suspend fun pendingPayments(): ApiEnvelope<PendingListData>

    @POST("payments/notify")
    suspend fun notifyPending(): ApiEnvelope<MessageData>
}
