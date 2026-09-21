<template>
  <el-popover placement="bottom-end" :width="264" trigger="click">
    <template #reference>
      <button class="hue-toggle" type="button" aria-label="调整主题色相">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 256 256">
          <path
            d="M200.77,53.89A103.27,103.27,0,0,0,128,24h-1.07A104,104,0,0,0,24,128c0,43,26.58,79.06,69.36,94.17A32,32,0,0,0,136,192a16,16,0,0,1,16-16h46.21a31.81,31.81,0,0,0,31.2-24.88,104.43,104.43,0,0,0,2.59-24A103.28,103.28,0,0,0,200.77,53.89Zm13,93.71A15.89,15.89,0,0,1,198.21,160H152a32,32,0,0,0-32,32,16,16,0,0,1-21.31,15.07C62.49,194.3,40,164,40,128a88,88,0,0,1,87.09-88h.9a88.35,88.35,0,0,1,88,87.25A88.86,88.86,0,0,1,213.81,147.6ZM140,76a12,12,0,1,1-12-12A12,12,0,0,1,140,76ZM96,100A12,12,0,1,1,84,88,12,12,0,0,1,96,100Zm0,56a12,12,0,1,1-12-12A12,12,0,0,1,96,156Zm88-56a12,12,0,1,1-12-12A12,12,0,0,1,184,100Z" />
        </svg>
      </button>
    </template>

    <!-- 面板：即时预览 = CSS 变量更新即全站生效 -->
    <div class="hue-panel">
      <div class="hue-head">
        <span class="hue-preview" :style="{ background: 'var(--color-primary)' }"></span>
        <span class="hue-label">主题色相 {{ Math.round(hue) }}°</span>
        <button class="hue-reset" type="button" @click="resetHue">重置</button>
      </div>

      <el-slider class="hue-slider" :model-value="hue" :min="0" :max="360" :step="1" :show-tooltip="false"
        @input="setHue" />

      <div class="hue-presets">
        <button v-for="p in PRESETS" :key="p" type="button" class="preset-dot"
          :class="{ active: Math.round(hue) === p }" :style="{ background: `oklch(0.6 0.14 ${p})` }"
          :aria-label="`预设色相 ${p}°`" @click="setHue(p)" />
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { useThemeHue } from '@/composables/useThemeHue'

const { hue, setHue, resetHue } = useThemeHue()

// 红/橙/琥珀/绿(默认)/青/蓝/紫/粉
const PRESETS = [0, 30, 60, 163, 200, 250, 300, 330]
</script>

<style scoped>
/* 触发按钮：与 NavBar 的 .theme-toggle 同款 36px 圆钮（自含样式，避免依赖父组件 scoped） */
.hue-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
  transition:
    background-color 0.2s,
    color 0.2s;
}

.hue-toggle:hover {
  color: var(--color-primary);
  background: var(--color-background-mute);
}

/* ---------- 弹层面板（内容被 Teleport 到 body，元素自带本组件 scope 属性，scoped 可命中） ---------- */
.hue-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hue-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hue-preview {
  flex: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px var(--color-border);
}

.hue-label {
  flex: 1;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.hue-reset {
  border: none;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--color-background-mute);
  color: var(--color-text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition:
    background 0.2s,
    color 0.2s;
}

.hue-reset:hover {
  color: var(--color-primary);
  background: var(--color-primary-tint);
}

/* 彩虹滑轨：显式 13 档 oklch 渐变（跨浏览器确定性）；隐藏填充条露出全谱 */
.hue-slider :deep(.el-slider__runway) {
  background: linear-gradient(to right,
      oklch(0.6 0.14 0),
      oklch(0.6 0.14 30),
      oklch(0.6 0.14 60),
      oklch(0.6 0.14 90),
      oklch(0.6 0.14 120),
      oklch(0.6 0.14 150),
      oklch(0.6 0.14 180),
      oklch(0.6 0.14 210),
      oklch(0.6 0.14 240),
      oklch(0.6 0.14 270),
      oklch(0.6 0.14 300),
      oklch(0.6 0.14 330),
      oklch(0.6 0.14 360));
}

.hue-slider :deep(.el-slider__bar) {
  background: transparent;
}

.hue-slider :deep(.el-slider__button) {
  box-shadow: 0 0 0 2px var(--color-surface), inset 0 0 0 1px var(--color-border);
}

/* ---------- 预设色板 ---------- */
.hue-presets {
  display: flex;
  justify-content: space-between;
}

.preset-dot {
  flex: none;
  width: 22px;
  height: 22px;
  padding: 0;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px rgb(0 0 0 / 12%);
  transition:
    transform 0.15s,
    box-shadow 0.15s;
}

.preset-dot:hover {
  transform: scale(1.15);
}

.preset-dot.active {
  box-shadow:
    0 0 0 2px var(--color-surface),
    0 0 0 4px var(--color-primary);
}
</style>
