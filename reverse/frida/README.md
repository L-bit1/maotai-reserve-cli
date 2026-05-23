# Frida 动态逆向（i茅台 1.9.6）

需：**已 root 的 Android 真机** 或 **模拟器 + frida-server**，与电脑上 `frida-tools` 版本匹配。

## 安装

```bash
pip install frida-tools
# 手机侧：下载对应架构的 frida-server，adb push 后运行
```

## 用法

### 1. Hook 签名密钥（网易 KeyUtil）

```bash
cd "/Users/mac/Desktop/工作 /软件/茅台抢单软件"
frida -U -f com.moutai.mall -l reverse/frida/hook_sig_key.js --no-pause
```

在 App 内：发验证码 → 登录 → 进入预约页并提交一次。  
控制台会打印 `getOriginSigKey` 返回值（若类未被混淆改名）。

### 2. Hook MD5（核对 SALT）

```bash
frida -U -f com.moutai.mall -l reverse/frida/hook_md5.js --no-pause
```

观察登录/预约请求前 MD5 的输入字符串是否包含 `2af72f100c356273d46284f6fd1dfc08`。

### 3. 附加已运行的 App

```bash
frida -U com.moutai.mall -l reverse/frida/hook_sig_key.js
```

## 脱壳（进阶）

若 `hook_sig_key.js` 报 **ClassNotFound**，说明业务 DEX 尚未加载完成，可：

1. 先打开 App 到首页，再用 `frida -U com.moutai.mall -l ...` 附加  
2. 使用 `reverse/frida/dump_dex.js`（需配合内存搜索，仅作起点）

脱壳后的 dex 用 JADX 打开，搜索 `reservation`、`actParam`、`moutai519`。

## 注意

- 仅用于 **个人学习、维护自用脚本**，勿用于批量撞库或倒卖。  
- 部分机型带梆梆检测，Frida 可能被闪退，可尝试 hide 模块或换机。
