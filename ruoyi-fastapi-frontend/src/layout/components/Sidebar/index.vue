<template>
  <div :class="{ 'has-logo': showLogo }" class="sidebar-container">
    <logo v-if="showLogo" :collapse="isCollapse" />
    <el-scrollbar wrap-class="scrollbar-wrapper">
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :background-color="getMenuBackground"
        :text-color="getMenuTextColor"
        :unique-opened="true"
        :active-text-color="theme"
        :collapse-transition="false"
        mode="vertical"
        :class="sideTheme"
      >
        <sidebar-item
          v-for="(route, index) in sidebarRouters"
          :key="route.path + index"
          :item="route"
          :base-path="route.path"
        />
      </el-menu>
    </el-scrollbar>
  </div>
</template>

<script setup>
import Logo from './Logo'
import SidebarItem from './SidebarItem'
import useAppStore from '@/store/modules/app'
import useSettingsStore from '@/store/modules/settings'
import usePermissionStore from '@/store/modules/permission'

const route = useRoute();
const appStore = useAppStore()
const settingsStore = useSettingsStore()
const permissionStore = usePermissionStore()

const sidebarRouters = computed(() => permissionStore.sidebarRouters);
const showLogo = computed(() => settingsStore.sidebarLogo);
const sideTheme = computed(() => settingsStore.sideTheme);
const theme = computed(() => settingsStore.theme);
const isCollapse = computed(() => !appStore.sidebar.opened);

// 获取菜单背景色
const getMenuBackground = computed(() => {
  if (settingsStore.isDark) {
    return 'var(--sidebar-bg)';
  }
  return sideTheme.value === 'theme-dark' ? 'var(--sidebar-bg)' : 'var(--sidebar-light-bg)';
});

// 获取菜单文字颜色
const getMenuTextColor = computed(() => {
  if (settingsStore.isDark) {
    return 'var(--sidebar-text)';
  }
  return sideTheme.value === 'theme-dark' ? 'var(--sidebar-text)' : 'var(--sidebar-light-text)';
});

const activeMenu = computed(() => {
  const { meta, path } = route;
  if (meta.activeMenu) {
    return meta.activeMenu;
  }
  return path;
});
</script>

<style lang="scss" scoped>
.sidebar-container {
  background-color: v-bind(getMenuBackground);
  border-right: 1px solid var(--sidebar-border);
  
  .scrollbar-wrapper {
    background-color: transparent;
  }

  .el-menu {
    border: none;
    height: 100%;
    width: 100% !important;
    padding: 12px 10px 16px;
    
    .el-menu-item, .el-sub-menu__title {
      border-radius: 14px;
      margin-bottom: 4px;
      height: 44px;
      line-height: 44px;
      &:hover {
        background-color: var(--menu-hover, rgba(0, 0, 0, 0.06)) !important;
      }
    }

    .el-menu-item {
      color: v-bind(getMenuTextColor);
      font-weight: 500;
      
      &.is-active {
        color: var(--menu-active-text, #409eff);
        background-color: var(--menu-active-bg, rgba(0, 0, 0, 0.06)) !important;
      }
    }

    .el-sub-menu__title {
      color: v-bind(getMenuTextColor);
    }

    .el-sub-menu.is-active > .el-sub-menu__title {
      color: var(--menu-active-text, #409eff);
      background-color: var(--menu-active-bg, rgba(0, 0, 0, 0.06)) !important;
    }
  }
}
</style>
