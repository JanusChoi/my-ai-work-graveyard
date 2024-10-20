<!-- src/components/InputForm.vue -->
<template>
  <div class="input-form-container">
    <div class="input-form-wrapper">
      <div class="input-form">
        <input 
          v-model="word" 
          placeholder="输入你想要重新解释的汉语词汇" 
          @keyup.enter="submitWord"
          class="centered-input"
        />
        <div class="prompt-selector">
          <label v-for="prompt in prompts" :key="prompt.value" class="prompt-label">
            <input 
              type="radio" 
              :value="prompt.value" 
              v-model="selectedPrompt"
              @change="updateSelectedPrompt"
            >
            <span>{{ prompt.label }}</span>
          </label>
          <span></span>
        </div>
        <button @click="submitWord" :disabled="isInputInvalid">提交</button>
      </div>
      <p v-if="errorMessage" class="error-message">错误信息: {{ errorMessage }}</p>
    </div>
    <div class="attribution">
      基于李继刚老师分享的Claude提示词制作
    </div>
  </div>
</template>

<script>
import sensitiveWordFilter from '../utils/sensitiveWordFilter';

export default {
  data() {
    return {
      word: '',
      errorMessage: '',
      containsSensitiveWord: false,
      selectedPrompt: 'hanyu_xinjie',
      backgroundSvg: `
        <svg width="100%" height="100%" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#E6F3FF;stop-opacity:1" />
              <stop offset="100%" style="stop-color:#B3D9FF;stop-opacity:1" />
            </linearGradient>
            <filter id="floating">
              <feTurbulence type="fractalNoise" baseFrequency="0.01" numOctaves="3" result="noise" />
              <feDisplacementMap in="SourceGraphic" in2="noise" scale="5" xChannelSelector="R" yChannelSelector="G" />
            </filter>
          </defs>
          <rect width="100%" height="100%" fill="url(#bg-gradient)" />
          <circle cx="75%" cy="20%" r="10%" fill="#FFD700" filter="url(#floating)">
            <animate attributeName="cy" values="20%;22%;20%" dur="4s" repeatCount="indefinite" />
          </circle>
          <path d="M70% 20% Q75% 26% 80% 20%" stroke="#000" stroke-width="1%" fill="none" filter="url(#floating)">
            <animate attributeName="d" values="M70% 20% Q75% 26% 80% 20%;M70% 22% Q75% 28% 80% 22%;M70% 20% Q75% 26% 80% 20%" dur="4s" repeatCount="indefinite" />
          </path>
          <circle cx="72.5%" cy="17%" r="1.5%" fill="#000" filter="url(#floating)">
            <animate attributeName="cy" values="17%;19%;17%" dur="4s" repeatCount="indefinite" />
          </circle>
          <circle cx="77.5%" cy="17%" r="1.5%" fill="#000" filter="url(#floating)">
            <animate attributeName="cy" values="17%;19%;17%" dur="4s" repeatCount="indefinite" />
          </circle>
        </svg>
      `,
      prompts: [
        { value: 'hanyu_xinjie', label: '汉语新解' },
        { value: 'concept_remix', label: '揉碎概念' },
        { value: 'book_of_answers', label: '答案之书' },
        { value: 'internet_slang', label: '互联网黑话' },
        { value: 'toulmin_argument', label: '图尔敏论证' },
        { value: 'word_memory', label: '单词记忆' },
      ],
    }
    
  },
  computed: {
    isInputInvalid() {
      return this.word.trim() === '' || this.containsSensitiveWord;
    }
  },
  methods: {
    async submitWord() {
      // console.log('Submitting word:', this.word);
      if (this.word.trim() === '') {
        this.setErrorMessage('请输入有效的词汇');
      } else if (this.containsSensitiveWord) {
        this.setErrorMessage('输入内容包含敏感词，请修改');
      } else {
        this.setErrorMessage('');
        // console.log('Emitting submit event');
        this.$emit('submit', { word: this.word, promptType: this.selectedPrompt });
      }
    },
    setErrorMessage(message) {
      // console.log('Setting error message:', message);
      this.errorMessage = message;
    },
    checkSensitiveWord() {
      const result = sensitiveWordFilter.containsSensitiveWords(this.word);
      this.containsSensitiveWord = result;
      console.log('Contains sensitive word:', result);
      if (result) {
        this.setErrorMessage('输入内容包含敏感词，请修改');
      } else {
        this.setErrorMessage('');
      }
    },
    updateSelectedPrompt() {
      // 可以在这里添加任何需要在选择提示词类型改变时执行的逻辑
    }
  },
  watch: {
    word() {
      this.checkSensitiveWord();
    }
  },
  async created() {
    // console.log('InputForm component created');
    await sensitiveWordFilter.initialize();
    // console.log('SensitiveWordFilter initialization complete');
  }
}
</script>

<style scoped>
.input-form-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #E6F3FF;
  padding: 20px;
}

.input-form-wrapper {
  background: linear-gradient(to bottom, #ffffff, #E6F3FF);
  border-radius: 20px;
  padding: 30px;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
  width: 90%;
  max-width: 400px;
}

.input-form {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.centered-input {
  width: 100%;
  padding: 15px;
  font-size: 16px;
  text-align: center;
  border: 2px solid #BFE0FF;
  border-radius: 10px;
  margin-bottom: 20px;
  transition: all 0.3s ease;
}

.centered-input:focus {
  outline: none;
  border-color: #4CAF50;
  box-shadow: 0 0 10px rgba(76, 175, 80, 0.3);
}

.centered-input::placeholder {
  color: #A0A0A0;
}

button {
  padding: 12px 25px;
  font-size: 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

button:hover {
  background-color: #45a049;
  transform: translateY(-2px);
  box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
}

.attribution {
  margin-top: 20px;
  font-size: 12px;
  color: #7B7B7B;
  text-align: center;
}

.error-message {
  color: #ff0000;
  font-size: 14px;
  margin-top: 10px;
  border: 1px solid #ff0000;
  padding: 5px;
}

.prompt-selector {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  margin: 15px 0;
}

.prompt-label {
  margin: 5px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.prompt-label span {
  display: inline-block;
  padding: 8px 15px;
  border-radius: 10px;
  background-color: transparent;
  color: #333;
  transition: all 0.3s ease;
}

.prompt-label:hover span {
  background-color: #E6F3FF; /* 颜色 A: 淡蓝色 */
}

input[type="radio"] {
  display: none;
}

input[type="radio"]:checked + span {
  background-color: #4c4eaf;
  color: white;
}

button {
  /* 保持原有样式 */
}

.attribution {
  /* 保持原有样式 */
}

@media (max-width: 768px) {
  .prompt-label {
    margin: 3px;
  }
  
  .prompt-label span {
    padding: 6px 12px;
    font-size: 14px;
  }
}
</style>