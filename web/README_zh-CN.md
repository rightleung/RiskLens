# React + TypeScript + Vite

本模板提供了一个最小化设置，使 React 可以在 Vite 中运行，并支持热更新 (HMR) 及其附带的 ESLint 规则。

目前提供两个官方插件：

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) 使用 [Babel](https://babeljs.io/)（或在 [rolldown-vite](https://vite.dev/guide/rolldown) 中使用 [oxc](https://oxc.rs)）实现快速刷新。
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) 使用 [SWC](https://swc.rs/) 实现快速刷新。

## React Compiler

由于它对开发和构建性能的影响，此模板默认未启用 React Compiler。要添加它，请参阅[此文档](https://react.dev/learn/react-compiler/installation)。

## 扩展 ESLint 配置

如果你在开发生产级别的应用，我们建议更新配置以启用类型感知的代码检查规则：

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // 其他配置...

      // 移除 tseslint.configs.recommended 并替换为以下内容
      tseslint.configs.recommendedTypeChecked,
      // 或者，使用此配置以获得更严格的规则
      tseslint.configs.strictTypeChecked,
      // 也可以加上风格相关的约束
      tseslint.configs.stylisticTypeChecked,

      // 其他配置...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // 其他选项...
    },
  },
])
```

你也可以安装 [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) 和 [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) 来实现针对 React 特定规则的支持。
