const { createApp } = Vue;

const app = createApp({
    data() {
        return {
            activeTab: 'home',
            currentFile: null,
            previewUrl: '',
            recommendStyles: ['治愈', '文艺', '伤感', '俏皮', '复古', '氛围感', '极简'],
            styleColors: {
                '治愈': '#ccff00',
                '文艺': '#00d9ff',
                '伤感': '#ff9500',
                '俏皮': '#ff006e',
                '复古': '#ffdd00',
                '氛围感': '#b537f2',
                '极简': '#e0e0e0'
            },
            selectedInstruction: '',
            customInstruction: '',
            loading: false,
            result: { scene: '', caption: '', imgPath: '' },
            copyBtnText: '复制文案',
            historyList: []
        };
    },
    mounted() {
        this.historyList = [];
    },
    methods: {
        handleFileChange(e) {
            const file = e.target.files[0];
            if (!file) return;
            this.previewUrl = URL.createObjectURL(file);
            this.currentFile = file;
            this.result = { scene: '', caption: '', imgPath: '' };
        },

        selectStyle(s) {
            this.selectedInstruction = this.selectedInstruction === s ? '' : s;
        },

        async generateCaption() {
            if (!this.currentFile) {
                alert("请上传图片");
                return;
            }
            this.loading = true;

            const fileClone = new File([this.currentFile], this.currentFile.name, {
                type: this.currentFile.type
            });

            let fd = new FormData();
            fd.append('file', fileClone);
            const instruction = [this.selectedInstruction, this.customInstruction].filter(x => x).join('，');
            fd.append('instruction', instruction || '治愈');

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
            this.copyBtnText = "已复制";
            setTimeout(() => {
                this.copyBtnText = "复制文案";
            }, 1500);
        },

        saveHistory() {
            let item = {
                imgPath: this.result.imgPath,
                scene: this.result.scene,
                caption: this.result.caption,
                style: this.selectedInstruction || this.customInstruction || '默认',
                time: new Date().toLocaleString()
            };
            this.historyList.unshift(item);
            if (this.historyList.length > 10) {
                this.historyList = this.historyList.slice(0, 10);
            }
        },

        loadHistory(item) {
            this.previewUrl = item.imgPath;
            this.result.scene = item.scene;
            this.result.caption = item.caption;
            this.result.imgPath = item.imgPath;
            this.selectedInstruction = item.style;
            this.currentFile = null;
        }
    }
});

app.config.compilerOptions.delimiters = ['[[', ']]'];
app.mount('#app');
