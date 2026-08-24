import js from '@eslint/js'
import typescript from '@typescript-eslint/eslint-plugin'
import typescriptParser from '@typescript-eslint/parser'
import vuePlugin from 'eslint-plugin-vue'
import vueEslintParser from 'vue-eslint-parser'
import prettier from 'eslint-plugin-prettier'

const testingGlobals = {
  describe: 'readonly',
  it: 'readonly',
  test: 'readonly',
  expect: 'readonly',
  vi: 'readonly',
  beforeEach: 'readonly',
  afterEach: 'readonly',
  beforeAll: 'readonly',
  afterAll: 'readonly',
}

const browserGlobals = {
  fetch: 'readonly',
  document: 'readonly',
  window: 'readonly',
  navigator: 'readonly',
  localStorage: 'readonly',
  sessionStorage: 'readonly',
  setTimeout: 'readonly',
  clearTimeout: 'readonly',
  setInterval: 'readonly',
  clearInterval: 'readonly',
  Promise: 'readonly',
  alert: 'readonly',
  URLSearchParams: 'readonly',
  FormData: 'readonly',
  URL: 'readonly',
  confirm: 'readonly',
  requestAnimationFrame: 'readonly',
  HTMLInputElement: 'readonly',
  HTMLElement: 'readonly',
  HTMLImageElement: 'readonly',
  HTMLCanvasElement: 'readonly',
  HTMLDivElement: 'readonly',
  HTMLButtonElement: 'readonly',
  HTMLSelectElement: 'readonly',
  BeforeUnloadEvent: 'readonly',
  HTMLAnchorElement: 'readonly',
  HTMLIFrameElement: 'readonly',
  HTMLTableElement: 'readonly',
  Element: 'readonly',
  DOMRect: 'readonly',
  Document: 'readonly',
  Event: 'readonly',
  DragEvent: 'readonly',
  KeyboardEvent: 'readonly',
  MouseEvent: 'readonly',
  InputEvent: 'readonly',
  FocusEvent: 'readonly',
  File: 'readonly',
  FileList: 'readonly',
  FileReader: 'readonly',
  Blob: 'readonly',
  NodeJS: 'readonly',
  Response: 'readonly',
  crypto: 'readonly',
  atob: 'readonly',
  btoa: 'readonly',
  IntersectionObserver: 'readonly',
  IntersectionObserverInit: 'readonly',
  DOMParser: 'readonly',
  NodeFilter: 'readonly',
  Node: 'readonly',
  Text: 'readonly',
  MutationObserver: 'readonly',
  ResizeObserver: 'readonly',
  CustomEvent: 'readonly',
  AbortController: 'readonly',
  AbortSignal: 'readonly',
  RequestInit: 'readonly',
}

const nodeGlobals = {
  __dirname: 'readonly',
  __filename: 'readonly',
  process: 'readonly',
  Buffer: 'readonly',
  global: 'readonly',
  module: 'readonly',
  require: 'readonly',
  exports: 'readonly',
}

const rules = {
  'array-bracket-newline': ['error', 'consistent'],
  'array-bracket-spacing': ['error', 'never'],
  'brace-style': ['error', '1tbs', { allowSingleLine: true }],
  'comma-dangle': [
    'error',
    {
      arrays: 'always-multiline',
      objects: 'always-multiline',
      imports: 'always-multiline',
      exports: 'always-multiline',
      functions: 'never',
    },
  ],
  'comma-spacing': ['error', { before: false, after: true }],
  curly: ['error', 'multi-line', 'consistent'],
  'eol-last': ['error'],
  'key-spacing': ['error'],
  'keyword-spacing': ['error'],
  'no-multi-spaces': ['error', { ignoreEOLComments: false }],
  'object-curly-spacing': ['error', 'always'],
  'object-property-newline': ['error', { allowAllPropertiesOnSameLine: true }],
  quotes: ['error', 'single', { avoidEscape: true }],
  'space-before-blocks': 'error',
  semi: ['error', 'never'],
  // Disabled: prettier owns all semicolon formatting (including leading-semicolon ASI guards)
  'no-extra-semi': 'off',
}

export default [
  // Global ignores — flat config doesn't read .eslintignore
  {
    ignores: ['.claude/**', 'dist/**', 'node_modules/**', 'public/**', '**/*.d.ts'],
  },

  // Base JS config
  js.configs.recommended,

  // Configuration for plain JavaScript files (.js, .jsx, .mjs)
  {
    files: ['**/*.js', '**/*.jsx', '**/*.mjs'],
    languageOptions: {
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: false,
        },
      },
      globals: {
        console: 'readonly',
        ...browserGlobals,
        ...nodeGlobals,
      },
    },
    rules: {
      semi: ['error', 'never'],
      quotes: ['error', 'single'],
      'no-unused-vars': 'off',
    },
  },

  // Configuration for plain TypeScript files (.ts, .tsx)
  {
    files: ['**/*.ts', '**/*.tsx'],
    plugins: {
      '@typescript-eslint': typescript,
      prettier,
    },
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: false,
        },
      },
      globals: {
        console: 'readonly',
        ...browserGlobals,
      },
    },
    rules: {
      semi: ['error', 'never'],
      quotes: ['error', 'single'],
      // Disabled: conflicts with prettier's own formatting
      '@typescript-eslint/indent': 'off',
      '@typescript-eslint/no-unused-vars': 'off',
      'no-unused-vars': 'off',
      'prettier/prettier': 'error',
    },
  },

  // Configuration for Vue single-file components (.vue)
  {
    files: ['**/*.vue'],
    plugins: {
      vue: vuePlugin,
      '@typescript-eslint': typescript,
      prettier,
    },
    languageOptions: {
      parser: vueEslintParser,
      parserOptions: {
        // Delegate <script> block parsing to the TypeScript parser
        parser: typescriptParser,
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: false,
        },
      },
      globals: {
        defineProps: 'readonly',
        defineEmits: 'readonly',
        defineExpose: 'readonly',
        withDefaults: 'readonly',
        console: 'readonly',
        ...browserGlobals,
      },
    },
    // Spread in Vue 3 recommended flat configuration from eslint-plugin-vue
    ...vuePlugin.configs['flat/vue3-recommended'],
    rules: {
      // Disabled: conflicts with prettier's own formatting
      '@typescript-eslint/indent': 'off',
      '@typescript-eslint/no-unused-vars': 'off',
      'no-unused-vars': 'off',
      'vue/multi-word-component-names': 'off',
      // XSS sink — pinned to warn so it always surfaces (see vue-security skill).
      // Warn (not error) keeps `eslint .` green in verify/CI while forcing the
      // "did you sanitize this?" conversation on every v-html binding.
      'vue/no-v-html': 'warn',
      'prettier/prettier': 'error',
    },
  },
  {
    files: ['**/*.{ts,tsx,vue}'],
    rules,
  },

  // Vitest/Playwright test files
  {
    files: ['**/*.test.ts', '**/*.spec.ts', 'e2e/**/*.ts'],
    languageOptions: {
      globals: {
        ...testingGlobals,
      },
    },
  },

  // Configuration for Node.js config files
  {
    files: ['*.config.js', '*.config.ts', '*.config.mjs'],
    languageOptions: {
      globals: {
        ...nodeGlobals,
        ...browserGlobals,
      },
    },
  },

  // CommonJS files (mock scripts, cjs utilities)
  {
    files: ['**/*.cjs'],
    languageOptions: {
      globals: {
        console: 'readonly',
        ...nodeGlobals,
        ...browserGlobals,
      },
    },
  },
]
