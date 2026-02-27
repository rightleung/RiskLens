# React + TypeScript + Vite

このテンプレートは、ReactをViteで実行し、HMR（Hot Module Replacement）およびいくつかのESLintルールをサポートするための最小限のセットアップを提供します。

現在、公式プラグインが2つ提供されています：

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) は [Babel](https://babeljs.io/)（または [rolldown-vite](https://vite.dev/guide/rolldown) と使用する場合 [oxc](https://oxc.rs)）を利用してFast Refreshを実現します。
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) は [SWC](https://swc.rs/) を利用してFast Refreshを実現します。

## React Compiler

開発およびビルドのパフォーマンスへの影響があるため、React Compilerはこのテンプレートではデフォルトで有効になっていません。追加する場合は、[こちらのドキュメント](https://react.dev/learn/react-compiler/installation)を参照してください。

## ESLint 設定の拡張

プロダクションレベルのアプリケーションを開発する場合、型を認識するLintルールを有効にするように設定を更新することをお勧めします：

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // 他の設定...

      // tseslint.configs.recommended を削除し、以下に置き換える
      tseslint.configs.recommendedTypeChecked,
      // より厳格なルールが必要な場合は、こちらを使用する
      tseslint.configs.strictTypeChecked,
      // スタイル関連のルールを追加する場合は、こちらを使用する
      tseslint.configs.stylisticTypeChecked,

      // 他の設定...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // その他のオプション...
    },
  },
])
```

また、[eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) と [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) をインストールすることで、React特有のルールをサポートすることもできます。
