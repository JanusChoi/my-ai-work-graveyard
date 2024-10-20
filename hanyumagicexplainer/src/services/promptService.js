// src/services/promptService.js
import { prompts } from '../config/prompts';

export const promptService = {
  getPromptConfig(promptType) {
    return prompts[promptType] || prompts.hanyu_xinjie; // 默认使用汉语新解
  },

  getSystemPrompt(promptType) {
    const config = this.getPromptConfig(promptType);
    return config.systemPrompt;
  },

  getAllPromptTypes() {
    return Object.keys(prompts);
  },

  getAllPromptLabels() {
    return Object.entries(prompts).map(([value, prompt]) => ({
      value,
      label: prompt.label
    }));
  }
};