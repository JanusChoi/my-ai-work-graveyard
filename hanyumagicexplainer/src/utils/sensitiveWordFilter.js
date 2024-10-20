// src/utils/sensitiveWordFilter.js
import sensitiveWords from '!raw-loader!@/data/sensi_words.txt';

class SensitiveWordFilter {
    constructor() {
        this.sensitiveMap = new Map();
        this.initialized = false;
        this.wordCount = 0;
    }

    async initialize() {
        // console.time('SensitiveWordFilter Initialization');
        if (this.initialized) {
            // console.log('SensitiveWordFilter already initialized');
            // console.timeEnd('SensitiveWordFilter Initialization');
            return;
        }

        const words = await this.loadSensitiveWords();
        this.setSensitiveWords(words);

        this.initialized = true;
        // console.log(`SensitiveWordFilter initialized with ${this.wordCount} words`);
        // console.timeEnd('SensitiveWordFilter Initialization');
    }

    async loadSensitiveWords() {
        // console.time('Loading Sensitive Words');
        try {
            //   const response = await fetch(sensitiveWords);
            //   const text = await response.text();
            const words = sensitiveWords
                .split('\n')
                .flatMap(line => line.split(/\s+/))
                .filter(word => word.trim() !== '');
            // console.log('Processed words:', words); // 新增：输出处理后的词列表
            // console.log(`Loaded ${words.length} sensitive words`);
            // console.timeEnd('Loading Sensitive Words');
            return words;
        } catch (error) {
            // console.error('Failed to load sensitive words:', error);
            // console.timeEnd('Loading Sensitive Words');
            return [];
        }
    }

    setSensitiveWords(words) {
        // console.time('Setting Sensitive Words');
        this.sensitiveMap = this.createSensitiveMap(words);
        this.wordCount = words.length;
        // console.log(`Set ${this.wordCount} sensitive words`);
        // console.timeEnd('Setting Sensitive Words');
    }

    createSensitiveMap(sensitiveWords) {
        const map = new Map();
        for (const word of sensitiveWords) {
            let currentMap = map;
            for (const char of word) {
                if (!currentMap.has(char)) {
                    currentMap.set(char, new Map());
                }
                currentMap = currentMap.get(char);
            }
            currentMap.set('isEnd', true);
        }
        return map;
    }

    containsSensitiveWords(text) {
        // console.time('Checking Sensitive Words');
        if (!this.initialized) {
            // console.warn('SensitiveWordFilter not initialized');
            // console.timeEnd('Checking Sensitive Words');
            return false;
        }

        for (let i = 0; i < text.length; i++) {
            const result = this.checkSensitiveWord(text, i);
            if (result.found) {
                // console.log(`Sensitive word found: ${result.word}`);
                // console.timeEnd('Checking Sensitive Words');
                return true;
            }
        }
        // console.log('No sensitive words found');
        // console.timeEnd('Checking Sensitive Words');
        return false;
    }

    checkSensitiveWord(text, startIndex) {
        let currentMap = this.sensitiveMap;
        let lastMatchIndex = -1;
        let matchLength = 0;
    
        for (let i = startIndex; i < text.length; i++) {
            const char = text[i];
            if (!currentMap.has(char)) {
                break;
            }
            currentMap = currentMap.get(char);
            matchLength++;
            if (currentMap.get('isEnd')) {
                lastMatchIndex = i;
            }
        }
    
        if (lastMatchIndex !== -1 && matchLength > 1) {
            // 检查是否是完整的词
            const matchedWord = text.slice(startIndex, lastMatchIndex + 1);
            if (this.isCompleteWord(text, startIndex, lastMatchIndex)) {
                return { found: true, word: matchedWord };
            }
        }
    
        return { found: false };
    }

    isCompleteWord(text, start, end) {
        // 检查词的前后是否有其他字符
        const isWordChar = (char) => /[\p{L}\p{N}]/u.test(char);
        const prevChar = start > 0 ? text[start - 1] : '';
        const nextChar = end < text.length - 1 ? text[end + 1] : '';
        return (!isWordChar(prevChar) && !isWordChar(nextChar));
      }
}

const filter = new SensitiveWordFilter();

export default filter;