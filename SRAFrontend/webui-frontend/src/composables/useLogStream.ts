import type { Ref } from 'vue'
import { nextTick, onUnmounted } from 'vue'
import type { ScrollbarInstance } from 'element-plus'

export function useLogStream(logs: Ref<string[]>, token: Ref<string>, logScrollbar: Ref<ScrollbarInstance | undefined>) {
  let eventSource: EventSource | null = null

  async function scrollLogsToBottom() {
    await nextTick()
    logScrollbar.value?.setScrollTop(999999)
  }

  function closeStream() {
    eventSource?.close()
    eventSource = null
  }

  function toggleStream(enabled: string | number | boolean, onError: () => void) {
    closeStream()
    if (!enabled) return

    eventSource = new EventSource('/Task/logs/stream?access_token=' + encodeURIComponent(token.value))
    eventSource.onmessage = async (event) => {
      logs.value.push(event.data)
      if (logs.value.length > 600) logs.value.splice(0, logs.value.length - 600)
      await scrollLogsToBottom()
    }
    eventSource.onerror = () => {
      onError()
      closeStream()
    }
  }

  onUnmounted(closeStream)

  return {
    closeStream,
    scrollLogsToBottom,
    toggleStream
  }
}

