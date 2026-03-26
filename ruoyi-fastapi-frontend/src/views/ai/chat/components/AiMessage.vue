<template>
  <div class="ai-message-container">
    <div v-if="reasoningContent" class="reasoning-section">
      <div class="reasoning-header" @click="toggleReasoning">
        <el-icon :class="{ 'is-expanded': isReasoningExpanded }"
          ><ArrowRight
        /></el-icon>
        <span>深度思考过程</span>
        <span class="reasoning-status" v-if="!isThinkingComplete"
          >思考中...</span
        >
      </div>
      <div v-show="isReasoningExpanded" class="reasoning-content">
        <MarkdownRender :content="reasoningContent" :is-dark="false" />
      </div>
    </div>
    <div class="ai-message-content">
      <MarkdownRender :content="content" :is-dark="false" />
    </div>
    <div
      v-if="loading && !content && !reasoningContent"
      class="typing-indicator"
    >
      <span></span>
      <span></span>
      <span></span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { MarkdownRender } from "markstream-vue";
import { enableKatex, enableMermaid } from "markstream-vue";
import "markstream-vue/index.css";
import "katex/dist/katex.min.css";

enableMermaid();
enableKatex();

const props = defineProps({
  content: {
    type: String,
    default: "",
  },
  reasoningContent: {
    type: String,
    default: "",
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const isReasoningExpanded = ref(true);

const isThinkingComplete = computed(() => {
  return !!props.content;
});

function toggleReasoning() {
  isReasoningExpanded.value = !isReasoningExpanded.value;
}
</script>

<style lang="scss">
.ai-message-container {
  --ai-message-text: #1a2536;
  --ai-message-muted: #66758c;
  --ai-inline-code-bg: rgba(42, 92, 198, 0.08);
  --ai-reasoning-border: rgba(42, 92, 198, 0.14);
  --ai-reasoning-bg: linear-gradient(180deg, rgba(42, 92, 198, 0.08), rgba(42, 92, 198, 0.03));
  --ai-reasoning-panel: rgba(255, 255, 255, 0.72);
  width: 100%;

  .ai-message-content {
    font-size: 14px;
    line-height: 1.8;
    color: var(--ai-message-text);
    overflow-wrap: break-word;
    word-break: break-word;

    :deep(*) {
      color: inherit;
    }

    :deep(p) {
      margin: 0 0 12px;
    }

    :deep(pre) {
      border-radius: 16px;
      overflow: hidden;
      box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.14);
    }

    :deep(code:not(pre code)) {
      padding: 2px 6px;
      border-radius: 8px;
      background: var(--ai-inline-code-bg);
    }
  }
}

.reasoning-section {
  margin-bottom: 16px;
  border: 1px solid var(--ai-reasoning-border);
  background: var(--ai-reasoning-bg);
  border-radius: 16px;
  padding: 12px 14px;

  .reasoning-header {
    display: flex;
    align-items: center;
    cursor: pointer;
    color: var(--ai-message-muted);
    font-size: 13px;
    user-select: none;
    font-weight: 600;

    .el-icon {
      margin-right: 6px;
      transition: transform 0.3s;
      &.is-expanded {
        transform: rotate(90deg);
      }
    }

    .reasoning-status {
      margin-left: 10px;
      font-size: 12px;
      color: var(--app-accent);
      animation: blink 1.5s infinite;
    }
  }

  .reasoning-content {
    font-size: 13px;
    color: var(--ai-message-text);
    margin-top: 10px;
    padding: 10px 12px;
    background-color: var(--ai-reasoning-panel);
    border-radius: 12px;
    overflow-wrap: break-word;
    word-break: break-word;
  }
}

@keyframes blink {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
  100% {
    opacity: 1;
  }
}

.typing-indicator {
  display: flex;
  align-items: center;
  padding: 10px 0 4px;

  span {
    display: inline-block;
    width: 7px;
    height: 7px;
    background-color: var(--el-color-primary);
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out both;
    margin-right: 6px;

    &:nth-child(1) {
      animation-delay: -0.32s;
    }

    &:nth-child(2) {
      animation-delay: -0.16s;
    }
  }
}

@keyframes typing {
  0%,
  80%,
  100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}
</style>
