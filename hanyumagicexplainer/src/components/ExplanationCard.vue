<!-- src/components/ExplanationCard.vue -->
<template>
  <div class="explanation-card-wrapper">
    <div class="explanation-card">
      <button @click="$emit('back')" class="back-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
      </button>
      <div ref="svgContainer" class="svg-container" :style="svgContainerStyle"></div>
    </div>
    <button @click="saveImage" class="save-button">保存图片</button>
  </div>
</template>
  
<script>
import { generateQRCode } from '../utils/qrCode';
import { v4 as uuidv4 } from 'uuid';
import { promptService } from '../services/promptService';

export default {
  props: {
    svgCode: {
      type: String,
      required: true
    },
    explanation: {
      type: String,
      default: '无法获取解释'
    },
    promptType: {
      type: String,
      required: true
    }
  },
  computed: {
    svgContainerStyle() {
      const config = promptService.getPromptConfig(this.promptType);
      return {
        width: `${config.width}px`,
        height: `${config.height}px`,
        margin: config.margin || '0 auto',
        backgroundColor: config.backgroundColor || 'transparent'
      };
    }
  },
  mounted() {
    this.renderSVG();
  },
  watch: {
    svgCode() {
      this.$nextTick(() => {
        this.renderSVG();
      });
    }
  },
  methods: {
    async renderSVG() {
      if (!this.svgCode) {
        // console.error('No SVG code provided');
        this.$refs.svgContainer.innerHTML = '<p>No content to display</p>';
        return;
      }

      try {
        // 解析原始 SVG
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(this.svgCode, 'image/svg+xml');
        const svgElement = svgDoc.documentElement;

        // 设置 SVG 尺寸
        const config = promptService.getPromptConfig(this.promptType);
        svgElement.setAttribute('width', config.width);
        svgElement.setAttribute('height', config.height);
        svgElement.setAttribute('viewBox', `0 0 ${config.width} ${config.height}`);
        svgElement.setAttribute('preserveAspectRatio', 'xMidYMid meet');

        // 为二维码预留空间
        const qrCodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        qrCodeGroup.setAttribute('transform', 'translate(20, 5) scale(0.8)');
        svgElement.appendChild(qrCodeGroup);

        // 生成二维码
        const qrCodeSvg = await generateQRCode('https://hanyumagicexplainer.net/');
        qrCodeGroup.innerHTML = qrCodeSvg;

        // 替换所有的 xlink:href 为 href
        svgElement.innerHTML = svgElement.innerHTML.replace(/xlink:href/g, 'href');

        // 渲染修改后的 SVG
        this.$refs.svgContainer.innerHTML = '';
        this.$refs.svgContainer.appendChild(svgElement);
      } catch (error) {
        console.error('SVG rendering error:', error);
        this.$refs.svgContainer.innerHTML = '<p>Error rendering content</p>';
      }
    },
    async saveImage() {
      // console.log('开始保存图片');
      const svgElement = this.$refs.svgContainer.querySelector('svg');
      if (!svgElement) {
        // console.error('No SVG element found');
        return;
      }

      try {
        // 克隆 SVG 元素
        // console.log('克隆 SVG 元素');
        // 克隆SVG并应用样式
        const clonedSvg = this.prepareClonedSVG(svgElement);
        // 处理动画
        this.handleSVGAnimations(clonedSvg);

        // 转换SVG为图片
        const imgBlob = await this.svgToImage(clonedSvg);

        // 生成唯一文件名
        const fileName = `hanyu_xinjie_${uuidv4()}.png`;

        // 保存或分享图片
        await this.saveOrShareImage(imgBlob, fileName);

      } catch (error) {
        console.error('保存图片时发生错误:', error);
        this.showErrorMessage('保存图片失败，请重试');
      }
    },
    prepareClonedSVG(svgElement) {
      const clonedSvg = svgElement.cloneNode(true);
      
      // 确保所有样式都被应用
      const styles = this.getComputedStyles(svgElement);
      clonedSvg.setAttribute('style', styles);

      // 递归地应用样式到所有子元素
      this.applyStylesToChildren(clonedSvg, svgElement);

      return clonedSvg;
    },

    getComputedStyles(element) {
      const styles = window.getComputedStyle(element);
      return Array.from(styles).reduce((str, property) => {
        return `${str}${property}:${styles.getPropertyValue(property)};`;
      }, '');
    },

    applyStylesToChildren(clonedElement, originalElement) {
      const clonedChildren = clonedElement.children;
      const originalChildren = originalElement.children;
      for (let i = 0; i < clonedChildren.length; i++) {
        const styles = this.getComputedStyles(originalChildren[i]);
        clonedChildren[i].setAttribute('style', styles);
        this.applyStylesToChildren(clonedChildren[i], originalChildren[i]);
      }
    },

    handleSVGAnimations(svgElement) {
      // 移除所有动画元素，或将其转换为静态表示
      svgElement.querySelectorAll('animate, animateTransform, animateMotion').forEach(el => {
        // 这里可以根据需要处理动画，例如将其设置为最终状态或移除
        el.remove();
      });
    },

    async svgToImage(svgElement) {
      const svgData = new XMLSerializer().serializeToString(svgElement);
      const svgBlob = new Blob([svgData], {type: 'image/svg+xml;charset=utf-8'});
      const svgUrl = URL.createObjectURL(svgBlob);

      return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          canvas.width = svgElement.getAttribute('width');
          canvas.height = svgElement.getAttribute('height');
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0);
          canvas.toBlob(resolve, 'image/png');
        };
        img.onerror = reject;
        img.src = svgUrl;
      });
    },

    async saveOrShareImage(blob, fileName) {
      if (navigator.share && navigator.canShare({ files: [new File([blob], fileName, { type: 'image/png' })] })) {
        try {
          await navigator.share({
            files: [new File([blob], fileName, { type: 'image/png' })],
            title: '汉语新解释',
            text: '分享我的汉语新解释'
          });
        } catch (error) {
          // console.error('Share failed:', error);
          this.fallbackSave(blob, fileName);
        }
      } else {
        this.fallbackSave(blob, fileName);
      }
    },

    fallbackSave(blob, fileName) {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },

    showErrorMessage(message) {
      // 实现一个错误提示的方法，可以使用 toast 或 alert
      alert(message);
    }
  }
}
</script>

<style scoped>
.explanation-card-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  padding: 20px;
  background-color: #f5f5f5;
  overflow: hidden;
}

.explanation-card {
  flex-grow: 1;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.svg-container {
  flex-grow: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: visible;
}

.svg-container svg {
  max-width: 100%;
  height: auto;
}

.back-button {
  position: absolute;
  top: 10px;
  left: 10px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 5px;
  z-index: 10;
}

.save-button {
  display: block;
  width: 100%;
  max-width: 600px;
  padding: 10px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  margin: 10px auto 0;
}

.save-button:hover {
  background-color: #45a049;
}

@media (max-width: 768px) {
  .explanation-card {
    padding: 15px;
  }

  .save-button {
    font-size: 14px;
  }
}
</style>