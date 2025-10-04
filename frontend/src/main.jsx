import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// 過濾掉特定的 console 錯誤訊息
const originalError = console.error;
console.error = (...args) => {
  const errorMessage = args[0];

  // 過濾掉 React.Fragment 的警告
  if (typeof errorMessage === 'string' &&
      errorMessage.includes('Invalid prop') &&
      errorMessage.includes('React.Fragment')) {
    return;
  }

  // 過濾掉 Mapbox 的空錯誤
  if (args[0] === 'Mapbox detailed error:' &&
      args[1]?.message === undefined) {
    return;
  }

  // 其他錯誤正常顯示
  originalError.apply(console, args);
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
