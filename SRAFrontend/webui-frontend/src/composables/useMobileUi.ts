import { onMounted, onUnmounted, ref } from 'vue'

export function useMobileUi() {
  const isMobileUi = ref(false)
  let mobileMediaQuery: MediaQueryList | null = null

  function updateMobileUi() {
    const ua = navigator.userAgent || ''
    const mobileUa = /Android|iPhone|iPad|iPod|Mobile|Windows Phone/i.test(ua)
    isMobileUi.value = mobileUa || window.innerWidth <= 760
  }

  onMounted(() => {
    updateMobileUi()
    mobileMediaQuery = window.matchMedia('(max-width: 760px)')
    mobileMediaQuery.addEventListener?.('change', updateMobileUi)
    window.addEventListener('resize', updateMobileUi)
  })

  onUnmounted(() => {
    mobileMediaQuery?.removeEventListener?.('change', updateMobileUi)
    window.removeEventListener('resize', updateMobileUi)
  })

  return {
    isMobileUi
  }
}

