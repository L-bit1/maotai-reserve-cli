package com.maotai.reserve

import android.app.Application
import com.maotai.reserve.data.SessionManager

class MaotaiApp : Application() {
    lateinit var session: SessionManager
        private set

    override fun onCreate() {
        super.onCreate()
        session = SessionManager(this)
    }
}
