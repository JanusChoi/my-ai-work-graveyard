<!-- src/App.vue -->
<template>
  <div id="app">
    <InputForm @submit="handleSubmit" v-if="!svgCode" />
    <ExplanationCard 
      v-else
      :explanation="explanation"
      :svgCode="svgCode"
      :promptType="currentPromptType"
      @back="resetForm"
    />
    <LoadingSpinner :isLoading="isLoading" />
  </div>
</template>

<script>
import InputForm from './components/InputForm.vue'
import ExplanationCard from './components/ExplanationCard.vue'
import LoadingSpinner from './components/LoadingSpinner.vue'
import { getExplanation } from './services/api'

export default {
  name: 'App',
  components: {
    InputForm,
    ExplanationCard,
    LoadingSpinner
  },
  data() {
    return {
      explanation: '',
      svgCode: '',
      isLoading: false,
      currentPromptType: ''
    }
  },
  methods: {
    async handleSubmit({ word, promptType }) {
      this.isLoading = true;
      try {
        const result = await getExplanation(word, promptType);
        // console.log('API result:', result);
        this.explanation = result.explanation || '';
        this.svgCode = result.svgCode || '';
        // console.log('Received explanation:', this.explanation);
        // console.log('Received SVG code:', this.svgCode);
      } catch (error) {
        console.error('Error getting explanation:', error);
        // 处理错误，例如显示错误消息给用户
        this.explanation = '获取解释时出错';
        this.svgCode = '<svg width="400" height="300"></svg>';
      } finally {
        this.isLoading = false;
      }
    },
    resetForm() {
      this.explanation = '';
      this.svgCode = '';
      this.currentPromptType = '';
    }
  },
  mounted() {
    document.title = '汉语新解'; // 在组件挂载时设置页面标题
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>