# Bank of AI — 优化版官网

基于 [bankofai.io](https://bankofai.io/) 的页面分析与优化重构。

## 项目结构

```
├── index.html          # 主页面
├── css/
│   └── style.css       # 样式文件
├── js/
│   └── main.js         # 交互逻辑
├── assets/             # 静态资源目录
└── README.md
```

## 技术栈

- **HTML5** — 语义化标签、结构化数据 (JSON-LD)
- **CSS3** — CSS Custom Properties、Grid/Flexbox、动画、响应式设计
- **Vanilla JS** — 零依赖，原生 JavaScript

## 优化要点

### 1. 性能优化
- 零 JS 框架依赖，纯原生实现，首屏加载极快
- CSS 使用 Custom Properties 统一管理，减少重复代码
- Canvas 粒子动画尊重 `prefers-reduced-motion` 偏好设置
- 图片使用 SVG 内联，无额外 HTTP 请求
- 字体使用 `preconnect` 预连接优化加载

### 2. SEO 优化
- 完整的 Open Graph 和 Twitter Card 元标签
- JSON-LD 结构化数据
- 语义化 HTML5 标签 (header, nav, main, section, article, footer)
- Canonical URL 设置
- 合理的标题层级 (h1 → h2 → h3 → h4)

### 3. 响应式设计
- Mobile-first 设计理念
- 三个断点：480px / 768px / 1024px
- 移动端全屏导航菜单
- `clamp()` 实现流式字体大小

### 4. 用户体验
- 固定导航栏 + 毛玻璃效果
- 平滑滚动 + 锚点导航
- Intersection Observer 驱动的滚动动画
- 交互式粒子网格背景
- 悬浮卡片效果 + 辉光阴影
- 清晰的 CTA 按钮层次

### 5. 可访问性
- ARIA 标签和 role 属性
- 键盘可导航
- 高对比度文字
- `prefers-reduced-motion` 媒体查询支持
- 语义化按钮和链接

### 6. 视觉设计
- 深色主题 + 蓝紫渐变色系（契合 AI/Crypto 行业风格）
- 毛玻璃态 (Glassmorphism) 导航和卡片
- 代码窗口组件展示 SDK 用法
- 一致的间距和排版系统
- 渐变文字高亮关键信息

## 本地预览

使用任何静态文件服务器即可预览：

```bash
# Python
python3 -m http.server 8080

# Node.js
npx serve .
```

然后访问 `http://localhost:8080`。
