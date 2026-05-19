const { createApp } = Vue;

createApp({
    data() {
        return {
            activeTab: 'home', // 当前激活的标签页
            imageBlob: null,   // 缓存的图片 Blob
            previewUrl: '',    // 图片预览地址
            selectedStyle: '治愈', // 选中的文案风格
            loading: false,    // 加载状态
            result: {          // 识别结果
                scene: '',
                caption: ''
            }
        };
    },
    methods: {
        // 处理文件选择
        handleFileChange(e) {
            const file = e.target.files[0];
            if (!file) return;

            // 释放之前的预览 URL，防止内存泄漏
            if (this.previewUrl) {
                URL.revokeObjectURL(this.previewUrl);
            }

            this.previewUrl = URL.createObjectURL(file);

            // 缓存图片为 Blob，解决同图换风格报错问题
            fetch(this.previewUrl)
                .then(res => res.blob())
                .then(blob => {
                    this.imageBlob = blob;
                    // 切换图片后清空之前的结果
                    this.result = { scene: '', caption: '' };
                });
        },

        // 提交生成文案
        async generateCaption() {
            if (!this.imageBlob) {
                alert('请先选择一张风景图片');
                return;
            }

            this.loading = true;
            this.result = { scene: '', caption: '' };

            const formData = new FormData();
            formData.append('file', this.imageBlob, 'scene.jpg');
            formData.append('style', this.selectedStyle);

            try {
                const response = await fetch('/predict', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('服务器响应错误');
                }

                const data = await response.json();
                this.result = data;
            } catch (error) {
                alert('生成失败：' + error.message);
            } finally {
                this.loading = false;
            }
        }
    },
    // 组件销毁时释放资源
    beforeUnmount() {
        if (this.previewUrl) {
            URL.revokeObjectURL(this.previewUrl);
        }
    }
}).mount('#app');