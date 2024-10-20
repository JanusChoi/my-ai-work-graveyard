// src/services/api.js
import axios from 'axios';
import { promptService } from './promptService';

const API_URL = process.env.VUE_APP_OPENROUTER_URL;
const API_KEY = process.env.VUE_APP_OPENROUTER_API_KEY;

function fixSvgUrlEncoding(svgCode) {
  // 修复 URL 编码问题
  return svgCode.replace(/&(?!amp;|lt;|gt;|quot;|apos;)/g, '&amp;');
}

function parseResponse(content) {
  console.log('Parsing response...')

  // 更新正则表达式以匹配实际输出格式
  const explanationMatch = content.match(/(.*?)\n([\s\S]*?)\n\nSVG代码.*$/);
  const svgMatch = content.match(/<svg([\s\S]*?)svg>/);

  // console.log('Explanation Match:', explanationMatch)
  // console.log('SVG Match:', svgMatch)
  
  let explanation = '无法获取解释';
  if (explanationMatch && explanationMatch[2]) {
    explanation = explanationMatch[2].trim();
  } else {
    // 如果无法匹配到解释，尝试提取第一行作为解释
    const firstLine = content.split('\n')[0];
    if (firstLine && firstLine.startsWith('解释：')) {
      explanation = firstLine.replace('解释：', '').trim();
    }
  }
  let svgCode = '';
  if (svgMatch && svgMatch[0]) {
    svgCode = fixSvgUrlEncoding(svgMatch[0].trim());
  }

  return { explanation, svgCode };
}

export async function getExplanation(word, promptType) {
  const systemPrompt = promptService.getSystemPrompt(promptType);
  const prompt = `请为这个汉语词汇提供一个新颖而有创意的解释：${word}\n\n${systemPrompt}`;

  try {
    console.log('Sending request to OpenRouter API...')
    const response = await axios.post(API_URL, {
      model: "anthropic/claude-3-sonnet-20240229",
      messages: [{ role: "system", content: systemPrompt }, { role: "user", content: prompt }]
    }, {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    console.log('Received response from OpenRouter API')
    const content = response.data.choices[0].message.content;
    // console.log('LLM Response:', content)

    const result = parseResponse(content);

    // console.log('Parsed Explanation:', result.explanation)
    // console.log('Parsed SVG Code:', result.svgCode)

    return result;
  } catch (error) {
    console.error('Error running getExplanation:', error);
    if (error.response) {
      console.error('Error response:', error.response.data)
    }
    throw error;
  }
}