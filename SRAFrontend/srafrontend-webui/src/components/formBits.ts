import { defineComponent, h } from 'vue'
import { ElSwitch } from 'element-plus'

export const TaskHeader = defineComponent({
  props: {
    title: { type: String, required: true },
    desc: { type: String, required: true },
    modelValue: { type: Boolean, required: true }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () =>
      h('div', { class: 'task-heading' }, [
        h('div', [h('h3', props.title), h('p', props.desc)]),
        h(ElSwitch, {
          modelValue: props.modelValue,
          'onUpdate:modelValue': (value: string | number | boolean) => emit('update:modelValue', Boolean(value)),
          activeText: '启用',
          inactiveText: '关闭'
        })
      ])
  }
})

export const SwitchField = defineComponent({
  props: {
    label: { type: String, required: true },
    active: { type: String, required: true },
    inactive: { type: String, required: true },
    modelValue: { type: Boolean, required: true }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () =>
      h('div', { class: 'field switch-field' }, [
        h('span', props.label),
        h(ElSwitch, {
          modelValue: props.modelValue,
          'onUpdate:modelValue': (value: string | number | boolean) => emit('update:modelValue', Boolean(value)),
          activeText: props.active,
          inactiveText: props.inactive
        })
      ])
  }
})

