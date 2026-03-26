<template>
  <el-menu class="topbar-menu" :ellipsis="false" :default-active="activeMenu" :active-text-color="theme" mode="horizontal">
    <sidebar-item :key="route.path + index" v-for="(route, index) in topMenus" :item="route" :base-path="route.path" />

    <el-sub-menu index="more" class="el-sub-menu__hide-arrow" v-if="moreRoutes.length > 0">
      <template #title>
        <span>更多菜单</span>
      </template>
      <sidebar-item :key="route.path + index" v-for="(route, index) in moreRoutes" :item="route" :base-path="route.path" />
    </el-sub-menu>
  </el-menu>
</template>

<script setup>
import SidebarItem from '../Sidebar/SidebarItem'
import useAppStore from '@/store/modules/app'
import useSettingsStore from '@/store/modules/settings'
import usePermissionStore from '@/store/modules/permission'

const route = useRoute()
const appStore = useAppStore()
const settingsStore = useSettingsStore()
const permissionStore = usePermissionStore()

const sidebarRouters = computed(() => permissionStore.sidebarRouters)
const theme = computed(() => settingsStore.theme)
const device = computed(() => appStore.device)
const activeMenu = computed(() => {
  const { meta, path } = route
  if (meta.activeMenu) {
    return meta.activeMenu
  }
  return path
})

const visibleNumber = ref(5)
const topMenus = computed(() => {
  return permissionStore.sidebarRouters.filter((f) => !f.hidden).slice(0, visibleNumber.value)
})
const moreRoutes = computed(() => {
  return permissionStore.sidebarRouters.filter((f) => !f.hidden).slice(visibleNumber.value, sidebarRouters.value.length - visibleNumber.value)
})
function setVisibleNumber() {
  const width = document.body.getBoundingClientRect().width / 3
  visibleNumber.value = parseInt(width / 85)
}

onMounted(() => {
  window.addEventListener('resize', setVisibleNumber)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', setVisibleNumber)
})

onMounted(() => {
  setVisibleNumber()
})
</script>

<style lang="scss">
.topbar-menu.el-menu--horizontal {
  display: flex;
  align-items: center;
  height: 56px;
  border-bottom: none !important;
  background: transparent !important;
}

.topbar-menu.el-menu--horizontal .el-submenu__title,
.topbar-menu.el-menu--horizontal .el-menu-item {
  height: 40px !important;
  line-height: 40px !important;
  padding: 0 12px !important;
  margin: 0 6px !important;
  border-radius: 12px;
  color: var(--navbar-text-muted) !important;
  transition: background 0.3s, color 0.3s;
}

.topbar-menu.el-menu--horizontal > .el-menu-item {
  float: left;
}

.topbar-menu.el-menu--horizontal > .el-sub-menu .el-sub-menu__title {
  float: left;
}

.topbar-menu.el-menu--horizontal > .el-menu-item:not(.is-disabled):hover,
.topbar-menu.el-menu--horizontal > .el-menu-item:not(.is-disabled):focus,
.topbar-menu.el-menu--horizontal > .el-sub-menu .el-sub-menu__title:hover,
.topbar-menu.el-menu--horizontal > .el-sub-menu .el-sub-menu__title:focus {
  background: var(--navbar-hover) !important;
  color: var(--navbar-text) !important;
}

.topbar-menu.el-menu--horizontal > .el-menu-item.is-active,
.topbar-menu.el-menu--horizontal > .el-sub-menu.is-active .el-sub-menu__title {
  border-bottom: none !important;
  background: var(--navbar-active-bg) !important;
  color: var(--navbar-active-text) !important;
}

.el-sub-menu.is-active .svg-icon,
.el-menu-item.is-active .svg-icon + span,
.el-sub-menu.is-active .svg-icon + span,
.el-sub-menu.is-active .el-sub-menu__title span {
  color: var(--navbar-active-text);
}

.topbar-menu .el-sub-menu .el-sub-menu__icon-arrow {
  position: static;
  margin-left: 8px;
  margin-top: 0px;
  display: block !important;
}
</style>
