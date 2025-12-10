package com.example.something.network

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.http.*

data class UploadResponse(
    val filename: String,
    val image_url: String,
    val timestamp: String,
    val final_verdict: FinalVerdict,
    val checks: Checks,
    val phash: String?
)

data class FinalVerdict(
    val fraud: Boolean,
    val reasons: List<String>,
    val accepted: Boolean,
    val credit_id: String?
)

data class Checks(
    val moire_detection: MoireDetection,
    val phash_duplicate: PhashDuplicate
)

data class MoireDetection(
    val fraud_detected: Boolean,
    val score: Double?,
    val fft_score: Double?,
    val reason: String?,
    val verdict: String
)

data class PhashDuplicate(
    val is_duplicate: Boolean,
    val total_checked: Int,
    val duplicates_found: Int,
    val closest_distance: Int?,
    val error: String?,
    val verdict: String
)

interface ApiService {
    @Multipart
    @POST("upload")
    fun uploadImage(
        @Part image: MultipartBody.Part,
        @Part("latitude") latitude: RequestBody,
        @Part("longitude") longitude: RequestBody,
        @Part("device_id") deviceId: RequestBody? = null,
        @Part("timestamp") timestamp: RequestBody? = null
    ): Call<UploadResponse>

    @GET("test")
    fun testConnection(): Call<Map<String, Any>>
}