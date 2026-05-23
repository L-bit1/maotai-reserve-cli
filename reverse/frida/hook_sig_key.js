/**
 * Hook 网易易盾 KeyUtil.getOriginSigKey（libyxsec.so）
 * 用法: frida -U -f com.moutai.mall -l hook_sig_key.js --no-pause
 */
'use strict';

function log(msg) {
  console.log('[imaotai] ' + msg);
}

function hookKeyUtil() {
  try {
    var KeyUtil = Java.use('com.netease.security.key.KeyUtil');
    if (KeyUtil.getOriginSigKey) {
      KeyUtil.getOriginSigKey.implementation = function () {
        var ret = this.getOriginSigKey();
        log('KeyUtil.getOriginSigKey() => ' + ret);
        return ret;
      };
      log('Hooked KeyUtil.getOriginSigKey');
    }
  } catch (e) {
    log('KeyUtil not found yet: ' + e + ' (retry after MTApp loads)');
  }
}

function hookOkHttp() {
  try {
    var Buffer = Java.use('okio.Buffer');
    var RealCall = Java.use('okhttp3.RealCall');
    RealCall.execute.implementation = function () {
      var req = this.request();
      var url = req.url().toString();
      if (url.indexOf('moutai519') >= 0) {
        log('HTTP ' + req.method() + ' ' + url);
        var body = req.body();
        if (body) {
          var buf = Buffer.$new();
          body.writeTo(buf);
          var s = buf.readUtf8();
          if (s && s.length < 4000) log('Body: ' + s);
        }
      }
      return this.execute();
    };
    log('Hooked okhttp3.RealCall.execute');
  } catch (e) {
    log('OkHttp hook skip: ' + e);
  }
}

Java.perform(function () {
  hookKeyUtil();
  hookOkHttp();
  // 壳加载较慢，延迟再试一次 KeyUtil
  setTimeout(function () {
    Java.perform(hookKeyUtil);
  }, 8000);
});
