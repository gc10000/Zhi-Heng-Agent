# 第三方来源与许可

课程底座及个人改造边界见[NOTICE.md](NOTICE.md)。前端实际文件映射、固定上游提交及改造内容见[复用清单](docs/reuse/manifest.json)，依赖精确版本和完整性见[锁文件](frontend/pnpm-lock.yaml)。没有将第三方组件描述为全部原创。

shadcn-vue复制/改编Dialog、ResizablePanelGroup及Sidebar，来源commit de1f76cbb4b319ea26b0dea175dc00c18fce3bd0。

```text
MIT License

Copyright (c) 2023 unovue

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

PDF.js 5.4.296使用Apache-2.0，分发时保留包内LICENSE和构建产物许可注释；本地worker随应用提供。Vue、Vue Router、Pinia、TanStack Vue Query、VueUse、Reka UI、Tailwind CSS、markdown-it等按其包内MIT许可证使用；包管理安装时保留各自LICENSE，未复制其产品源树。开发工具Vite、Vitest、Playwright、TypeScript、vue-tsc和openapi-typescript仅用于开发与构建，许可见对应包。后续M3新增实际封装文件在同一清单补记。
