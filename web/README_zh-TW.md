# React + TypeScript + Vite

本模板提供了一個最小化設置，使 React 可以在 Vite 中運行，並支持熱更新 (HMR) 及其附帶的 ESLint 規則。

目前提供兩個官方插件：

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) 使用 [Babel](https://babeljs.io/)（或在 [rolldown-vite](https://vite.dev/guide/rolldown) 中使用 [oxc](https://oxc.rs)）實現快速刷新。
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) 使用 [SWC](https://swc.rs/) 實現快速刷新。

## React Compiler

由於它對開發和構建性能的影響，此模板默認未啟用 React Compiler。要添加它，請參閱[此文檔](https://react.dev/learn/react-compiler/installation)。

## 擴展 ESLint 配置

如果你在開發生產級別的應用，我們建議更新配置以啟用類型感知的代碼檢查規則：

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // 其他配置...

      // 移除 tseslint.configs.recommended 並替換為以下內容
      tseslint.configs.recommendedTypeChecked,
      // 或者，使用此配置以獲得更嚴格的規則
      tseslint.configs.strictTypeChecked,
      // 也可以加上風格相關的約束
      tseslint.configs.stylisticTypeChecked,

      // 其他配置...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // 其他選項...
    },
  },
])
```

你也可以安裝 [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) 和 [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) 來實現針對 React 特定規則的支持。
