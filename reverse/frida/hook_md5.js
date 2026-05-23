/**
 * Hook MessageDigest MD5，打印含 moutai / 2af72f 的输入
 * 用法: frida -U -f com.moutai.mall -l hook_md5.js --no-pause
 */
'use strict';

var SALT_HINT = '2af72f';

Java.perform(function () {
  var MessageDigest = Java.use('java.security.MessageDigest');
  var md5Update = MessageDigest.update.overload('[B');
  var md5Digest = MessageDigest.digest.overload();

  MessageDigest.getInstance.overload('java.lang.String').implementation = function (algo) {
    var inst = this.getInstance(algo);
    if (algo === 'MD5') {
      var buf = [];
      md5Update.implementation = function (bytes) {
        buf.push(Java.use('java.lang.String').$new(bytes));
        return md5Update.call(this, bytes);
      };
      md5Digest.implementation = function () {
        var joined = buf.join('|');
        if (joined.indexOf(SALT_HINT) >= 0 || joined.indexOf('mobile') >= 0) {
          console.log('[imaotai MD5 input] ' + joined.substring(0, 500));
        }
        buf.length = 0;
        return md5Digest.call(this);
      };
    }
    return inst;
  };
  console.log('[imaotai] MD5 hook installed');
});
