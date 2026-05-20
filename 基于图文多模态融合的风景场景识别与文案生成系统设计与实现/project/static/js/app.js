const { createApp } = Vue;

createApp({
    data() {
        return {
            activeTab: 'home',
            imageBlob: null,
            previewUrl: '',
            selectedStyle: '治愈',
            loading: false,
            result: { scene: '', caption: '', imgPath: '' },
            copyBtnText: '复制文案',
            historyList: []
        };
    },
    delimiters: ['[[', ']]'],
    mounted() {
        this.loadHistoryFromLocal();
    },
    methods: {
        handleFileChange(e) {
            const file = e.target.files[0];
            if (!file) return;
            this.previewUrl = URL.createObjectURL(file);
            this.imageBlob = file;
            this.result = { scene: '', caption: '', imgPath: '' };
        },

        async generateCaption() {
            if (!this.imageBlob) {
                alert("请上传图片");
                return;
            }
            this.loading = true;
            let fd = new FormData();
            fd.append('file', this.imageBlob);
            fd.append('style', this.selectedStyle);

            try {
                let res = await fetch('/predict', { method: 'POST', body: fd });
                let data = await res.json();
                this.result = data;
                this.saveHistory();
            } catch (err) {
                alert("生成失败");
            }
            this.loading = false;
        },

        copyCaption() {
            navigator.clipboard.writeText(this.result.caption);
            this.copyBtnText = "✅ 已复制";
            setTimeout(() => this.copyBtnText = "复制文案", 1500);
        },

        saveHistory() {
            let item = {
                imgPath: this.result.imgPath,
                scene: this.result.scene,
                caption: this.result.caption,
                style: this.selectedStyle,
                time: new Date().toLocaleString()
            };
            let list = JSON.parse(localStorage.getItem('history') || '[]');
            list.unshift(item);
            if (list.length > 10) list = list.slice(0, 10);
            this.historyList = list;
            localStorage.setItem('history', JSON.stringify(list));
        },

        loadHistoryFromLocal() {
            this.historyList = JSON.parse(localStorage.getItem('history') || '[]');
        },

        loadHistory(item) {
            this.previewUrl = item.imgPath;
            this.result.scene = item.scene;
            this.result.caption = item.caption;
            this.result.imgPath = item.imgPath;
            this.selectedStyle = item.style;
        },

        reGenerate(item) {
            this.loadHistory(item);
            this.generateCaption();
        }
    }
}).mount('#app');