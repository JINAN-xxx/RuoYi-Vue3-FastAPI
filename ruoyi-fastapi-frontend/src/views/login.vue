<template>
  <div class="login-page">
    <section class="login-card">
      <div class="login-card__header">
        <div class="brand-badge">
          <img :src="logoSrc" alt="logo" class="brand-badge__logo" />
          <div>
            <p class="brand-badge__label">后台管理系统</p>
            <h1 class="brand-badge__title">{{ title }}</h1>
          </div>
        </div>
      </div>

      <div class="login-card__intro">
        <h3>欢迎登录</h3>
        <p>请输入账号密码登录系统。</p>
      </div>

      <el-form ref="loginRef" :model="loginForm" :rules="loginRules" class="login-form">
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            type="text"
            size="large"
            auto-complete="off"
            placeholder="请输入账号"
          >
            <template #prefix><svg-icon icon-class="user" class="el-input__icon input-icon" /></template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            size="large"
            auto-complete="off"
            placeholder="请输入密码"
            @keyup.enter="handleLogin"
          >
            <template #prefix><svg-icon icon-class="password" class="el-input__icon input-icon" /></template>
          </el-input>
        </el-form-item>
        <el-form-item v-if="captchaEnabled" prop="code">
          <div class="captcha-row">
            <el-input
              v-model="loginForm.code"
              size="large"
              auto-complete="off"
              placeholder="请输入验证码"
              @keyup.enter="handleLogin"
            >
              <template #prefix><svg-icon icon-class="validCode" class="el-input__icon input-icon" /></template>
            </el-input>
            <button type="button" class="captcha-card" @click="getCode">
              <img :src="codeUrl" alt="验证码" class="login-code-img" />
            </button>
          </div>
        </el-form-item>

        <div class="login-form__options">
          <el-checkbox v-model="loginForm.rememberMe">记住密码</el-checkbox>
          <router-link v-if="register" class="link-type" to="/register">立即注册</router-link>
        </div>

        <el-form-item class="login-form__submit">
          <el-button
            :loading="loading"
            size="large"
            type="primary"
            class="login-submit"
            @click.prevent="handleLogin"
          >
            <span v-if="!loading">进入系统</span>
            <span v-else>登录中...</span>
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-card__footer">
        <span>{{ footerContent }}</span>
      </div>
    </section>
  </div>
</template>

<script setup>
import { getCodeImg } from "@/api/login";
import Cookies from "js-cookie";
import { encrypt, decrypt } from "@/utils/jsencrypt";
import logoSrc from "@/assets/logo/logo.png";
import useUserStore from '@/store/modules/user'
import defaultSettings from '@/settings'

const title = import.meta.env.VITE_APP_TITLE;
const footerContent = defaultSettings.footerContent
const userStore = useUserStore();
const route = useRoute();
const router = useRouter();
const { proxy } = getCurrentInstance();

const loginForm = ref({
  username: "",
  password: "",
  rememberMe: false,
  code: "",
  uuid: ""
});

const loginRules = {
  username: [{ required: true, trigger: "blur", message: "请输入您的账号" }],
  password: [{ required: true, trigger: "blur", message: "请输入您的密码" }],
  code: [{ required: true, trigger: "change", message: "请输入验证码" }]
};

const codeUrl = ref("");
const loading = ref(false);
const captchaEnabled = ref(true);
const register = ref(false);
const redirect = ref(undefined);

watch(route, (newRoute) => {
    redirect.value = newRoute.query && newRoute.query.redirect;
}, { immediate: true });

function handleLogin() {
  proxy.$refs.loginRef.validate(valid => {
    if (valid) {
      loading.value = true;
      if (loginForm.value.rememberMe) {
        Cookies.set("username", loginForm.value.username, { expires: 30 });
        Cookies.set("password", encrypt(loginForm.value.password), { expires: 30 });
        Cookies.set("rememberMe", loginForm.value.rememberMe, { expires: 30 });
      } else {
        Cookies.remove("username");
        Cookies.remove("password");
        Cookies.remove("rememberMe");
      }
      userStore.login(loginForm.value).then(() => {
        const query = route.query;
        const otherQueryParams = Object.keys(query).reduce((acc, cur) => {
          if (cur !== "redirect") {
            acc[cur] = query[cur];
          }
          return acc;
        }, {});
        router.push({ path: redirect.value || "/", query: otherQueryParams });
      }).catch(() => {
        loading.value = false;
        if (captchaEnabled.value) {
          getCode();
        }
      });
    }
  });
}

function getCode() {
  getCodeImg().then(res => {
    captchaEnabled.value = res.captchaEnabled === undefined ? true : res.captchaEnabled;
    register.value = res.registerEnabled === undefined ? false : res.registerEnabled;
    if (captchaEnabled.value) {
      codeUrl.value = "data:image/gif;base64," + res.img;
      loginForm.value.uuid = res.uuid;
    }
  });
}

function getCookie() {
  const username = Cookies.get("username");
  const password = Cookies.get("password");
  const rememberMe = Cookies.get("rememberMe");
  loginForm.value = {
    username: username === undefined ? loginForm.value.username : username,
    password: password === undefined ? loginForm.value.password : decrypt(password),
    rememberMe: rememberMe === undefined ? false : Boolean(rememberMe)
  };
}

getCode();
getCookie();
</script>

<style lang='scss' scoped>
.login-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.05), transparent 26%),
    radial-gradient(circle at bottom right, rgba(15, 23, 42, 0.04), transparent 24%),
    linear-gradient(180deg, #f5f7fb 0%, #eef2f7 100%);
}

.login-card {
  width: min(440px, 100%);
  padding: 32px;
  border: 1px solid #e6ebf2;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.08);
}

.login-card__header {
  margin-bottom: 28px;
}

.brand-badge {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-badge__logo {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  padding: 8px;
  background: #eef4ff;
  border: 1px solid #dbe7fb;
}

.brand-badge__label {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: #7b8aa0;
}

.brand-badge__title {
  margin: 2px 0 0;
  font-size: 22px;
  font-weight: 700;
  color: #142136;
}

.login-card__intro {
  margin-bottom: 24px;
}

.login-card__intro h3 {
  margin: 0;
  font-size: 28px;
  color: #142136;
}

.login-card__intro p {
  margin: 8px 0 0;
  color: #607089;
  line-height: 1.7;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 52px;
  padding-inline: 14px;
  background: #ffffff;
  box-shadow: 0 0 0 1px #d8e0ec inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px rgba(38, 106, 233, 0.45) inset;
}

.input-icon {
  width: 14px;
  height: 14px;
  color: #5d6b82;
}

.captcha-row {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 138px;
  gap: 12px;
}

.captcha-card {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border: 1px solid #d8e0ec;
  border-radius: 14px;
  background: #f9fbfd;
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.captcha-card:hover {
  border-color: #c7d3e5;
}

.login-code-img {
  max-width: 100%;
  height: 40px;
  object-fit: contain;
}

.login-form__options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 2px 0 22px;
  font-size: 14px;
}

.link-type {
  color: var(--el-color-primary);
  font-weight: 600;
}

.login-form__submit {
  margin-bottom: 0 !important;
}

.login-submit {
  width: 100%;
  min-height: 52px;
  border: none;
  border-radius: 14px;
  background: #2f6fed;
  box-shadow: none;
}

.login-submit:hover {
  background: #255fd3;
}

.login-card__footer {
  margin-top: 24px;
  font-size: 12px;
  color: #7d8ba0;
  text-align: center;
  line-height: 1.8;
}

html.dark .login-page {
  background:
    radial-gradient(circle at top left, rgba(96, 165, 250, 0.1), transparent 24%),
    linear-gradient(180deg, #0f1724 0%, #111c2d 100%);
}

html.dark .login-card {
  background: #121c2d;
  border-color: rgba(148, 163, 184, 0.16);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.28);
}

html.dark .brand-badge__logo {
  background: rgba(96, 165, 250, 0.1);
  border-color: rgba(96, 165, 250, 0.16);
}

html.dark .brand-badge__label {
  color: rgba(220, 229, 243, 0.54);
}

html.dark .brand-badge__title,
html.dark .login-card__intro h3 {
  color: #f5f9ff;
}

html.dark .login-card__intro p,
html.dark .login-card__footer {
  color: rgba(220, 229, 243, 0.68);
}

html.dark .login-form :deep(.el-input__wrapper) {
  background: #162235;
  box-shadow: 0 0 0 1px rgba(160, 177, 204, 0.14) inset;
}

html.dark .captcha-card {
  background: #162235;
  border-color: rgba(160, 177, 204, 0.14);
}

@media (max-width: 768px) {
  .login-page {
    padding: 14px;
  }

  .login-card {
    padding: 24px 20px;
  }

  .login-card__header {
    margin-bottom: 24px;
  }

  .captcha-row {
    grid-template-columns: 1fr;
  }
}
</style>
