<!-- src/components/LoadingSpinner.vue -->
<template>
  <div class="loading-overlay" v-if="isLoading">
    <div class="cat">
      <div class="cat__body"></div>
      <div class="cat__body"></div>
      <div class="cat__tail"></div>
      <div class="cat__head"></div>
    </div>
    <p class="loading-text">AI生成中，请耐心等候</p>
  </div>
</template>

<script>
export default {
  name: 'LoadingSpinner',
  props: {
    isLoading: {
      type: Boolean,
      default: false
    }
  }
}
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(230, 220, 219, 0.7);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.cat {
  position: relative;
  width: 100%;
  max-width: 20em;
  overflow: hidden;
  background-color: #e6dcdb;
}

.cat::before {
  content: '';
  display: block;
  padding-bottom: 100%;
}

.cat__body, .cat__tail, .cat__head {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  animation: rotating 2.79s cubic-bezier(0.65, 0.54, 0.12, 0.93) infinite;
}

.cat__body::before, .cat__tail::before, .cat__head::before {
  content: '';
  position: absolute;
  width: 50%;
  height: 50%;
  background-size: 200%;
  background-repeat: no-repeat;
  background-image: url('https://images.weserv.nl/?url=i.imgur.com/M1raXX3.png&il');
}

.cat__head::before {
  top: 0;
  right: 0;
  background-position: 100% 0%;
  transform-origin: 0% 100%;
  transform: rotate(90deg);
}

.cat__tail {
  animation-delay: 0.2s;
}

.cat__tail::before {
  left: 0;
  bottom: 0;
  background-position: 0% 100%;
  transform-origin: 100% 0%;
  transform: rotate(-30deg);
}

.cat__body {
  animation-delay: 0.1s;
}

.cat__body:nth-of-type(2) {
  animation-delay: 0.2s;
}

.cat__body::before {
  right: 0;
  bottom: 0;
  background-position: 100% 100%;
  transform-origin: 0% 0%;
}

@keyframes rotating {
  from {
    transform: rotate(720deg);
  }
  to {
    transform: none;
  }
}

.loading-text {
  margin-top: 20px;
  font-size: 16px;
  color: #333;
}
</style>