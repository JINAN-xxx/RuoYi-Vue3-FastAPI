<template>
  <div class="sidebar-logo-container" :class="{ 'collapse': collapse }">
    <transition name="sidebarLogoFade">
      <router-link v-if="collapse" key="collapse" class="sidebar-logo-link" to="/">
        <img v-if="logo" :src="logo" class="sidebar-logo" />
        <h1 v-else class="sidebar-title">{{ title }}</h1>
      </router-link>
      <router-link v-else key="expand" class="sidebar-logo-link" to="/">
        <img v-if="logo" :src="logo" class="sidebar-logo" />
        <h1 class="sidebar-title">{{ title }}</h1>
      </router-link>
    </transition>
  </div>
</template>

<script setup>
import logo from '@/assets/logo/logo.png'
import useSettingsStore from '@/store/modules/settings'

defineProps({
  collapse: {
    type: Boolean,
    required: true
  }
})

const title = import.meta.env.VITE_APP_TITLE;
const settingsStore = useSettingsStore();
const sideTheme = computed(() => settingsStore.sideTheme);

// 获取Logo背景色
const getLogoBackground = computed(() => {
  if (settingsStore.isDark) {
    return 'var(--sidebar-surface)';
  }
  if (settingsStore.navType == 3) {
    return 'var(--frame-shell-bg-elevated)'
  }
  return sideTheme.value === 'theme-dark' ? 'var(--sidebar-surface)' : 'var(--sidebar-light-bg)';
});

// 获取Logo文字颜色
const getLogoTextColor = computed(() => {
  if (settingsStore.isDark) {
    return 'var(--sidebar-text-strong)';
  }
  if (settingsStore.navType == 3) {
    return 'var(--app-text-primary)'
  }
  return sideTheme.value === 'theme-dark' ? 'var(--sidebar-text-strong)' : 'var(--app-text-primary)';
});
</script>

<style lang="scss" scoped>
.sidebarLogoFade-enter-active {
  transition: opacity 1.5s;
}

.sidebarLogoFade-enter,
.sidebarLogoFade-leave-to {
  opacity: 0;
}

.sidebar-logo-container {
  position: relative;
  height: 56px;
  line-height: 56px;
  background:
    linear-gradient(135deg, rgba(var(--app-accent-rgb), 0.08), rgba(255, 255, 255, 0.02)),
    v-bind(getLogoBackground);
  text-align: left;
  overflow: hidden;
  border-bottom: 1px solid var(--sidebar-border);

  & .sidebar-logo-link {
    height: 100%;
    width: 100%;
    display: flex;
    align-items: center;
    padding: 0 18px;

    & .sidebar-logo {
      width: 32px;
      height: 32px;
      vertical-align: middle;
      margin-right: 12px;
      flex-shrink: 0;
    }

    & .sidebar-title {
      display: inline-block;
      margin: 0;
      color: v-bind(getLogoTextColor);
      font-weight: 700;
      line-height: 56px;
      font-size: 14px;
      font-family: "IBM Plex Sans", "PingFang SC", sans-serif;
      letter-spacing: 0.01em;
      vertical-align: middle;
    }
  }

  &.collapse {
    .sidebar-logo-link {
      justify-content: center;
      padding: 0;
    }

    .sidebar-logo {
      margin-right: 0px;
    }
  }
}
</style>
