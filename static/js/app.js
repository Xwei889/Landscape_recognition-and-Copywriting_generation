const { createApp } = Vue;

const app = createApp({
    data() {
        return {
            activeTab: 'home',
            currentFile: null,
            currentFiles: [],
            fileCount: 0,
            previewUrl: '',
            recommendStyles: ['治愈', '文艺', '伤感', '俏皮', '复古', '氛围感', '极简'],
            sceneOptions: ['海边', '山林', '落日', '古镇', '湖泊', '街巷', '草原', '城市天际线'],
            correctScene: '',
            statsData: null,
            historySearch: '',
            adminUsers: [],
            adminRecords: [],
            squareScene: '',
            selectedRecord: null,
            commentList: [],
            newComment: '',
            profileUser: null,
            profileShares: [],
            profileFans: 0,
            profileIsFollowing: false,
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
            result: { scene: '', caption: '', imgPath: '', recordId: null },
            copyBtnText: '复制文案',
            historyList: [],
            favoriteList: [],
            squareList: [],
            // ===== 用户体系 =====
            user: null,
            showAuthModal: false,
            authMode: 'login',
            authForm: { username: '', password: '' },
            showProfileModal: false,
            profileForm: { nickname: '', avatar: '' },
            pwdForm: { old_password: '', new_password: '' }
        };
    },
    mounted() {
        this.historyList = [];
        this.initAuth();
    },
    computed: {
        filteredHistory() {
            const kw = this.historySearch.trim();
            if (!kw) return this.historyList;
            return this.historyList.filter(h =>
                (h.scene || '').includes(kw) || (h.caption || '').includes(kw) || (h.style || '').includes(kw));
        }
    },
    methods: {
        // ===== 用户体系 =====
        async initAuth() {
            try {
                let res = await fetch('/api/me');
                let data = await res.json();
                if (data.ok) {
                    this.user = data.user;
                    this.fetchHistory();
                }
            } catch (e) {}
        },

        async fetchHistory() {
            try {
                let res = await fetch('/api/history');
                let data = await res.json();
                if (data.ok) this.historyList = data.list;
            } catch (e) {}
        },

        openAuth(mode) {
            this.authMode = mode;
            this.authForm = { username: '', password: '' };
            this.showAuthModal = true;
        },

        async submitAuth() {
            const url = this.authMode === 'login' ? '/api/login' : '/api/register';
            try {
                let res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.authForm)
                });
                let data = await res.json();
                if (data.ok) {
                    this.user = data.user;
                    this.showAuthModal = false;
                    this.fetchHistory();
                    alert(data.msg);
                } else {
                    alert(data.msg);
                }
            } catch (e) {
                alert("网络错误");
            }
        },

        async logout() {
            await fetch('/api/logout', { method: 'POST' });
            this.user = null;
            this.historyList = [];
            alert("已退出登录");
        },

        openProfile() {
            if (this.user) {
                this.profileForm.nickname = this.user.nickname || '';
                this.profileForm.avatar = this.user.avatar || '';
            }
            this.pwdForm = { old_password: '', new_password: '' };
            this.showProfileModal = true;
        },

        async saveProfile() {
            let res = await fetch('/api/profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.profileForm)
            });
            let data = await res.json();
            alert(data.msg);
            if (data.ok) this.initAuth();
        },

        async uploadAvatar(e) {
            const file = e.target.files[0];
            if (!file) return;
            let fd = new FormData();
            fd.append('file', file);
            let res = await fetch('/api/upload-avatar', { method: 'POST', body: fd });
            let data = await res.json();
            if (data.ok) {
                this.profileForm.avatar = data.url;
                this.initAuth();
                alert('头像已更新');
            } else {
                alert(data.msg);
            }
        },

        async changePwd() {
            let res = await fetch('/api/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.pwdForm)
            });
            let data = await res.json();
            alert(data.msg);
            if (data.ok) this.pwdForm = { old_password: '', new_password: '' };
        },

        handleFileChange(e) {
            const files = Array.from(e.target.files || []);
            this.currentFiles = files;
            this.fileCount = files.length;
            this.currentFile = files[0] || null;
            this.previewUrl = files.length ? URL.createObjectURL(files[0]) : '';
            this.result = { scene: '', caption: '', imgPath: '', recordId: null };
        },

        selectStyle(s) {
            this.selectedInstruction = this.selectedInstruction === s ? '' : s;
        },

        async generateCaption() {
            if (!this.currentFiles || !this.currentFiles.length) {
                alert("请上传图片");
                return;
            }
            this.loading = true;
            const instruction = [this.selectedInstruction, this.customInstruction].filter(x => x).join('，') || '治愈';
            let lastData = null;
            for (let i = 0; i < this.currentFiles.length; i++) {
                const fd = new FormData();
                fd.append('file', this.currentFiles[i]);
                fd.append('instruction', instruction);
                try {
                    let res = await fetch('/predict', { method: 'POST', body: fd });
                    lastData = await res.json();
                } catch (err) {}
            }
            if (lastData) {
                this.result = lastData;
                if (this.user) this.fetchHistory();
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
            this.previewUrl = item.img_path;
            this.result.scene = item.scene;
            this.result.caption = item.caption;
            this.result.imgPath = item.img_path;
            this.result.recordId = item.id;
            this.selectedInstruction = item.style;
            this.currentFile = null;
        },

        // ===== B 内容互动 =====
        async toggleFavorite() {
            if (!this.result.recordId) return;
            let res = await fetch('/api/favorite', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: this.result.recordId })
            });
            let data = await res.json();
            if (!data.ok && data.msg === '请先登录') { alert('请先登录'); return; }
            alert(data.msg);
        },

        async togglePublish() {
            if (!this.result.recordId) return;
            let res = await fetch('/api/publish', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: this.result.recordId })
            });
            let data = await res.json();
            if (!data.ok && data.msg === '请先登录') { alert('请先登录'); return; }
            alert(data.msg);
        },

        async editCaption() {
            if (!this.result.recordId) { alert('请先生成文案'); return; }
            let newCap = prompt('编辑文案：', this.result.caption);
            if (newCap === null) return;
            let res = await fetch('/api/edit-caption', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: this.result.recordId, caption: newCap })
            });
            let data = await res.json();
            alert(data.msg);
            if (data.ok) { this.result.caption = data.caption; this.fetchHistory(); }
        },

        async doRate(score) {
            if (!this.result.recordId) { alert('请先生成文案'); return; }
            let res = await fetch('/api/rating', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: this.result.recordId, score: score })
            });
            let data = await res.json();
            if (data.ok) alert('已给 ' + score + ' 星');
            else alert(data.msg);
        },

        toggleLike(recordId) {
            if (!this.user) { alert('请先登录'); return; }
            // 乐观更新：先改前端，再后台请求
            let item = this.squareList.find(x => x.id === recordId);
            if (item) {
                item.liked = !item.liked;
                item.like_cnt += item.liked ? 1 : -1;
            }
            fetch('/api/like', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: recordId })
            });
        },

        toggleSquareFavorite(recordId) {
            if (!this.user) { alert('请先登录'); return; }
            let item = this.squareList.find(x => x.id === recordId);
            if (item) {
                item.favorited = !item.favorited;
                item.fav_cnt = (item.fav_cnt || 0) + (item.favorited ? 1 : -1);
            }
            fetch('/api/favorite', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: recordId })
            });
        },

        async loadFavorites() {
            let res = await fetch('/api/favorites');
            let data = await res.json();
            if (data.ok) this.favoriteList = data.list;
        },

        async loadSquare() {
            let url = '/api/square';
            if (this.squareScene) url += '?scene=' + encodeURIComponent(this.squareScene);
            let res = await fetch(url);
            let data = await res.json();
            if (data.ok) this.squareList = data.list;
        },

        async openComments(record) {
            this.selectedRecord = record;
            this.newComment = '';
            let res = await fetch('/api/comments?record_id=' + record.id);
            let data = await res.json();
            this.commentList = data.ok ? data.list : [];
        },

        async submitComment() {
            if (!this.user) { alert('请先登录'); return; }
            if (!this.newComment.trim()) return;
            let res = await fetch('/api/comment', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: this.selectedRecord.id, content: this.newComment })
            });
            let data = await res.json();
            if (data.ok) {
                this.newComment = '';
                this.openComments(this.selectedRecord);
                this.loadSquare();
            } else alert(data.msg);
        },

        async openUserProfile(uid) {
            if (!uid) { alert('该用户已注销'); return; }
            let res = await fetch('/api/user/' + uid);
            let data = await res.json();
            if (data.ok) {
                this.profileUser = data.info;
                this.profileShares = data.shares;
                this.profileFans = data.fans;
                this.profileIsFollowing = data.is_following;
                this.activeTab = 'user';
            }
        },

        async toggleFollowFromProfile() {
            if (!this.user) { alert('请先登录'); return; }
            let res = await fetch('/api/follow', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.profileUser.id })
            });
            let data = await res.json();
            if (data.ok) {
                this.profileIsFollowing = data.following;
                this.openUserProfile(this.profileUser.id);
            } else alert(data.msg);
        },

        async doCorrect() {
            if (!this.result.recordId) { alert('请先生成文案'); return; }
            if (!this.correctScene) { alert('请选择正确场景'); return; }
            let res = await fetch('/api/correct', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: this.result.recordId, correct_scene: this.correctScene })
            });
            let data = await res.json();
            alert(data.msg);
            if (data.ok) this.correctScene = '';
        },

        async loadStats() {
            let res = await fetch('/api/stats');
            let data = await res.json();
            if (data.ok) {
                this.statsData = data.data;
                this.$nextTick(() => this.drawCharts());
            }
        },

        drawCharts() {
            if (typeof echarts === 'undefined') return;
            // 场景分布柱状图
            let c1 = echarts.init(document.getElementById('chartScene'));
            c1.setOption({
                title: { text: '场景分布', left: 'center', textStyle: { fontSize: 14, fontWeight: 900 } },
                tooltip: {},
                xAxis: { type: 'category', data: this.statsData.scene_dist.map(x => x.scene), axisLabel: { fontSize: 10 } },
                yAxis: { type: 'value' },
                series: [{ type: 'bar', data: this.statsData.scene_dist.map(x => x.c), itemStyle: { color: '#00d9ff', borderColor: '#000', borderWidth: 2 } }]
            });
            // 风格分布饼图
            let c2 = echarts.init(document.getElementById('chartStyle'));
            c2.setOption({
                title: { text: '文案风格占比', left: 'center', textStyle: { fontSize: 14, fontWeight: 900 } },
                tooltip: { trigger: 'item' },
                series: [{ type: 'pie', radius: '60%', data: this.statsData.style_dist.map(x => ({ name: x.style, value: x.c })) }]
            });
        },

        exportCSV() {
            if (!this.statsData) return;
            let rows = [['指标', '数值'], ['总生成数', this.statsData.total], ['注册用户', this.statsData.users],
                ['广场公开', this.statsData.public], ['收藏数', this.statsData.favorites], ['纠错数', this.statsData.corrections],
                ['准确率%', this.statsData.accuracy], [], ['场景', '次数']];
            this.statsData.scene_dist.forEach(s => rows.push([s.scene, s.c]));
            rows.push([], ['错判场景', '正确场景', '次数']);
            this.statsData.confusion.forEach(c => rows.push([c.wrong_scene, c.correct_scene, c.c]));
            let csv = '\ufeff' + rows.map(r => r.join(',')).join('\n');
            let blob = new Blob([csv], { type: 'text/csv' });
            let a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = '统计数据.csv';
            a.click();
        },

        async loadAdmin() {
            let r1 = await fetch('/api/admin/users');
            let d1 = await r1.json();
            if (d1.ok) this.adminUsers = d1.list;
            let r2 = await fetch('/api/admin/records');
            let d2 = await r2.json();
            if (d2.ok) this.adminRecords = d2.list;
            else alert(d2.msg || '无权限');
        },

        async adminDeleteRecord(rid) {
            if (!confirm('确定删除这条记录？')) return;
            let res = await fetch('/api/admin/delete-record', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: rid })
            });
            let data = await res.json();
            alert(data.msg);
            if (data.ok) this.loadAdmin();
        },

        async adminDeleteUser(uid) {
            if (!confirm('确定删除该用户及其全部数据？')) return;
            let res = await fetch('/api/admin/delete-user', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: uid })
            });
            let data = await res.json();
            alert(data.msg);
            if (data.ok) this.loadAdmin();
        }
    }
});

app.config.compilerOptions.delimiters = ['[[', ']]'];
app.mount('#app');
