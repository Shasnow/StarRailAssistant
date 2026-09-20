<template>
  <footer class="site-footer">
    <p class="footer-line">
      © {{ year }}
      {{ siteConfig.author }} · 
      <a class="footer-link" :href="siteConfig.licenseUrl" target="_blank"
        rel="noopener noreferrer">{{ siteConfig.license }}</a>
    </p>
    <p class="footer-line">
      Powered by
      <a class="footer-link" href="https://vuejs.org/" target="_blank" rel="noopener noreferrer">Vue 3</a>
      <span class="footer-dot">·</span>
      <a class="footer-link" href="https://vite.dev/" target="_blank" rel="noopener noreferrer">Vite</a>
    </p>
  </footer>
</template>

<script setup lang="ts">
import siteConfig from '@/configs/siteConfig'

const year = new Date().getFullYear()
</script>

<style scoped>
.site-footer {
  padding: 32px 24px 36px;
  text-align: center;
  font-size: 14px;
  color: var(--color-text);
  background: var(--page-bg);
  border-top: 2px dashed var(--color-border);
}

.footer-line {
  line-height: 1.9;
  opacity: 0.85;
}

.footer-link {
  color: var(--color-primary);
  text-decoration: none;
  transition: color 0.2s;
}

.footer-link:hover {
  color: var(--color-primary);
  text-decoration: underline;
}

.footer-dot {
  margin: 0 6px;
  opacity: 0.5;
}
</style>
